"""Owner-scoped application services for target allocations and rebalance simulations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from django.db import transaction

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.optimization.models import OptimizationRun, OptimizationRunStatus
from apps.portfolios.models import Portfolio
from apps.portfolios.services.current_valuation import (
    CurrentValuationError,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.rebalancing.models import RebalanceSimulation, TargetAllocation, TargetAllocationWeight
from portfolio_engine.rebalancing import (
    CurrentValue,
    RebalanceSchedule,
    RebalancingError,
    TargetWeight,
    evaluate_rebalance_rules,
    simulate_rebalance,
    validate_target_weights,
)


class RebalancingApplicationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TargetWeightInput:
    asset_id: UUID | None
    weight: float


@dataclass(frozen=True, slots=True)
class CreateTargetAllocationCommand:
    portfolio_id: UUID
    name: str
    weights: tuple[TargetWeightInput, ...]
    source_optimization_run_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateRebalanceSimulationCommand:
    portfolio_id: UUID
    target_allocation_id: UUID
    drift_threshold: float | None = None
    schedule: RebalanceSchedule | None = None
    previous_rebalance_date: date | None = None


class MarketBarQueryExecutor(Protocol):
    def __call__(self, *args: object, **kwargs: object) -> object: ...


@transaction.atomic
def create_target_allocation(
    *, user: User, command: CreateTargetAllocationCommand
) -> TargetAllocation:
    portfolio = Portfolio.objects.owned_by(user).get(id=command.portfolio_id)
    normalized = validate_target_weights(
        tuple(TargetWeight(asset_id=item.asset_id, weight=item.weight) for item in command.weights)
    )
    asset_ids = tuple(item.asset_id for item in normalized if item.asset_id is not None)
    assets = Asset.objects.in_bulk(asset_ids)
    if len(assets) != len(set(asset_ids)):
        raise RebalancingApplicationError(
            "Every target asset must reference an existing canonical asset."
        )
    for asset_id in asset_ids:
        asset = assets[asset_id]
        if (
            not asset.is_active
            or asset.currency != "USD"
            or asset.asset_type not in (AssetType.STOCK, AssetType.ETF)
        ):
            raise RebalancingApplicationError(
                "Target assets must be active canonical USD stocks or ETFs."
            )

    source_run = None
    if command.source_optimization_run_id is not None:
        source_run = OptimizationRun.objects.filter(
            id=command.source_optimization_run_id,
            user=user,
            portfolio=portfolio,
            status=OptimizationRunStatus.SUCCEEDED,
        ).first()
        if source_run is None:
            raise RebalancingApplicationError(
                "Source optimization run must be a successful owned run for this portfolio."
            )

    target = TargetAllocation(
        user=user,
        portfolio=portfolio,
        source_optimization_run=source_run,
        name=command.name.strip(),
    )
    target.full_clean()
    target.save()
    TargetAllocationWeight.objects.bulk_create(
        [
            TargetAllocationWeight(
                target=target,
                asset_id=item.asset_id,
                is_cash=item.asset_id is None,
                weight=Decimal(str(item.weight)),
            )
            for item in normalized
        ]
    )
    return TargetAllocation.objects.prefetch_related("weights__asset").get(id=target.id)


@transaction.atomic
def create_rebalance_simulation(
    *,
    user: User,
    command: CreateRebalanceSimulationCommand,
    as_of: datetime,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
) -> RebalanceSimulation:
    portfolio = Portfolio.objects.owned_by(user).get(id=command.portfolio_id)
    target = (
        TargetAllocation.objects.filter(
            id=command.target_allocation_id, user=user, portfolio=portfolio
        )
        .prefetch_related("weights__asset")
        .first()
    )
    if target is None:
        raise RebalancingApplicationError("Target allocation not found for this portfolio.")

    try:
        current = value_owned_portfolio(
            user=user,
            portfolio_id=portfolio.id,
            as_of=as_of,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            executor=execute_market_bar_query,
        )
    except CurrentValuationError as exc:
        raise RebalancingApplicationError(str(exc)) from exc

    if not current.is_complete or current.valuation is None or current.allocation is None:
        raise RebalancingApplicationError(
            "A complete positive current valuation is required for rebalance simulation."
        )
    if current.valuation.total_market_value <= 0.0:
        raise RebalancingApplicationError("Current investable portfolio value must be positive.")

    current_values = tuple(
        [
            CurrentValue(asset_id=item.asset_id, market_value=item.market_value)
            for item in current.valuation.positions
        ]
        + [CurrentValue(asset_id=None, market_value=current.valuation.cash_value)]
    )
    targets = tuple(
        TargetWeight(asset_id=weight.asset_id, weight=float(weight.weight))
        for weight in target.weights.all()
    )
    try:
        engine_result = simulate_rebalance(current_values, targets)
        rule_result = evaluate_rebalance_rules(
            engine_result.lines,
            decision_date=as_of.date(),
            threshold=command.drift_threshold,
            schedule=command.schedule,
            previous_rebalance_date=command.previous_rebalance_date,
        )
    except RebalancingError as exc:
        raise RebalancingApplicationError(str(exc)) from exc

    result = {
        "total_investable_value": engine_result.total_investable_value,
        "current_weight_sum": engine_result.current_weight_sum,
        "target_weight_sum": engine_result.target_weight_sum,
        "lines": [
            {
                "asset_id": str(line.asset_id) if line.asset_id is not None else None,
                "is_cash": line.asset_id is None,
                "current_value": line.current_value,
                "target_value": line.target_value,
                "current_weight": line.current_weight,
                "target_weight": line.target_weight,
                "absolute_drift": line.absolute_drift,
                "relative_drift": line.relative_drift,
                "trade_notional": line.trade_notional,
                "direction": line.direction.value,
            }
            for line in engine_result.lines
        ],
        "rules": {
            "threshold": rule_result.threshold,
            "threshold_triggered": rule_result.threshold_triggered,
            "schedule": rule_result.schedule.value if rule_result.schedule is not None else None,
            "previous_rebalance_date": (
                rule_result.previous_rebalance_date.isoformat()
                if rule_result.previous_rebalance_date is not None
                else None
            ),
            "decision_date": rule_result.decision_date.isoformat(),
            "schedule_due": rule_result.schedule_due,
        },
    }
    simulation = RebalanceSimulation(
        user=user,
        portfolio=portfolio,
        target_allocation=target,
        as_of=as_of,
        provider=current.provenance.provider,
        price_field=current.provenance.price_field,
        valuation_retrieved_at=current.provenance.retrieved_at,
        drift_threshold=(
            Decimal(str(command.drift_threshold)) if command.drift_threshold is not None else None
        ),
        schedule=(command.schedule.value if command.schedule is not None else ""),
        previous_rebalance_date=command.previous_rebalance_date,
        result=result,
        warnings=[
            {"code": warning.code.value, "message": warning.message} for warning in current.warnings
        ],
    )
    simulation.full_clean()
    simulation.save()
    return simulation
