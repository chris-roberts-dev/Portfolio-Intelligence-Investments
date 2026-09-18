"""Owner-scoped application services for Phase 5 target and rebalancing workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from django.db import transaction

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.contracts import (
    MarketBarBatchResult,
    MarketBarStatus,
    NormalizedMarketBarQuery,
    normalize_market_bar_query,
)
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
from apps.portfolios.services.ledger import replay_portfolio_ledger
from apps.rebalancing.models import (
    HistoricalRebalanceComparison,
    RebalanceSimulation,
    TargetAllocation,
    TargetAllocationWeight,
)
from portfolio_engine.config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.rebalancing import (
    CurrentValue,
    HistoricalPosition,
    HistoricalRebalanceComparisonResult,
    HistoricalRebalancePolicy,
    HistoricalRebalancePolicyResult,
    HistoricalRebalanceWarning,
    RebalanceLine,
    RebalanceSchedule,
    RebalancingError,
    TargetWeight,
    compare_historical_rebalancing,
    evaluate_rebalance_rules,
    simulate_rebalance,
    validate_target_weights,
)
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


class RebalancingApplicationError(ValueError):
    """Stable application-boundary failure for rebalancing workflows."""

    def __init__(self, message: str, *, code: str = "REBALANCING_ERROR") -> None:
        super().__init__(message)
        self.code = code


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


@dataclass(frozen=True, slots=True)
class CreateHistoricalRebalanceComparisonCommand:
    """Explicit historical comparison inputs for annual/quarterly/threshold rules."""

    portfolio_id: UUID
    target_allocation_id: UUID
    period_start: date
    period_end: date
    drift_threshold: float
    commission_rate: float = DEFAULT_COMMISSION_RATE
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE
    include_monthly: bool = False


class MarketBarQueryExecutor(Protocol):
    def __call__(
        self,
        query: NormalizedMarketBarQuery,
        *,
        resolver: AssetResolver,
        provider: MarketDataProvider,
    ) -> MarketBarBatchResult: ...


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
    target = _owned_target_allocation(
        user=user,
        portfolio=portfolio,
        target_allocation_id=command.target_allocation_id,
    )

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
    targets = _engine_targets(target)
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
        raise RebalancingApplicationError(str(exc), code=exc.code.value) from exc

    result = {
        "total_investable_value": engine_result.total_investable_value,
        "current_weight_sum": engine_result.current_weight_sum,
        "target_weight_sum": engine_result.target_weight_sum,
        "lines": [_serialize_rebalance_line(line) for line in engine_result.lines],
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


@transaction.atomic
def create_historical_rebalance_comparison(
    *,
    user: User,
    command: CreateHistoricalRebalanceComparisonCommand,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> HistoricalRebalanceComparison:
    """Persist an annual/quarterly/threshold historical comparison.

    The initial simulated state is the authoritative owned-portfolio ledger state
    observable at ``00:00 UTC`` on ``period_start``. Later real ledger activity is
    deliberately excluded from the hypothetical comparison and surfaced as a
    structured warning when present.
    """
    if command.period_start >= command.period_end:
        raise RebalancingApplicationError(
            "period_end must be later than period_start.",
            code="INVALID_DATE_RANGE",
        )

    portfolio = Portfolio.objects.owned_by(user).get(id=command.portfolio_id)
    target = _owned_target_allocation(
        user=user,
        portfolio=portfolio,
        target_allocation_id=command.target_allocation_id,
    )
    initial_as_of = datetime.combine(command.period_start, time.min, tzinfo=UTC)
    end_exclusive = datetime.combine(command.period_end + timedelta(days=1), time.min, tzinfo=UTC)
    ledger = replay_portfolio_ledger(portfolio, as_of=initial_as_of)

    target_weights = _engine_targets(target)
    initial_positions = tuple(
        HistoricalPosition(asset_id=position.asset_id, quantity=float(position.quantity))
        for position in ledger.positions
    )
    required_asset_ids: set[UUID] = {position.asset_id for position in initial_positions}
    required_asset_ids.update(
        target_weight.asset_id
        for target_weight in target_weights
        if target_weight.asset_id is not None
    )
    assets = Asset.objects.in_bulk(required_asset_ids)
    if len(assets) != len(required_asset_ids):
        raise RebalancingApplicationError(
            "Historical comparison references an unknown canonical asset.",
            code="UNKNOWN_ASSET",
        )
    symbols = tuple(assets[asset_id].symbol for asset_id in sorted(required_asset_ids, key=str))
    if len(set(symbols)) != len(symbols):
        raise RebalancingApplicationError(
            "Historical comparison requires unique canonical symbols for included assets.",
            code="AMBIGUOUS_ASSET_SYMBOL",
        )

    try:
        query = normalize_market_bar_query(
            symbols,
            start=command.period_start,
            end=command.period_end + timedelta(days=1),
            provider=provider_name,
        )
        batch = executor(query, resolver=resolver, provider=provider)
    except ValueError as exc:
        raise RebalancingApplicationError(
            str(exc),
            code="MARKET_DATA_QUERY_FAILED",
        ) from exc

    frames_by_asset: dict[UUID, PriceFrame] = {}
    market_warnings: list[dict[str, str]] = []
    for symbol_result in batch.results:
        if symbol_result.status is not MarketBarStatus.SUCCEEDED or symbol_result.asset_id is None:
            market_warnings.append(
                {
                    "code": f"MARKET_DATA_{symbol_result.status.value}",
                    "message": (
                        f"Historical comparison requires complete adjusted-close data for "
                        f"{symbol_result.symbol}."
                    ),
                }
            )
            continue
        frames_by_asset[symbol_result.asset_id] = symbol_result.bars

    if market_warnings or set(frames_by_asset) != required_asset_ids:
        detail = "; ".join(item["message"] for item in market_warnings) or (
            "Historical comparison market-data response did not contain every required asset."
        )
        raise RebalancingApplicationError(detail, code="INSUFFICIENT_MARKET_DATA")

    policies = [
        HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),
        HistoricalRebalancePolicy("quarterly", schedule=RebalanceSchedule.QUARTERLY),
        HistoricalRebalancePolicy("threshold", threshold=command.drift_threshold),
    ]
    if command.include_monthly:
        policies.insert(2, HistoricalRebalancePolicy("monthly", schedule=RebalanceSchedule.MONTHLY))

    try:
        engine_result = compare_historical_rebalancing(
            price_frames=frames_by_asset,
            initial_positions=initial_positions,
            initial_cash=float(ledger.cash_balance),
            targets=target_weights,
            policies=tuple(policies),
            commission_rate=command.commission_rate,
            slippage_rate=command.slippage_rate,
        )
    except RebalancingError as exc:
        raise RebalancingApplicationError(str(exc), code=exc.code.value) from exc

    warnings = [_serialize_warning(warning) for warning in engine_result.warnings]
    if portfolio.transactions.filter(
        occurred_at__gt=initial_as_of,
        occurred_at__lt=end_exclusive,
    ).exists():
        warnings.append(
            {
                "code": "ACTUAL_LEDGER_ACTIVITY_IGNORED",
                "message": (
                    "The hypothetical historical comparison starts from the ledger state at "
                    f"{initial_as_of.isoformat()} and does not apply later real portfolio "
                    "transactions during the comparison period."
                ),
            }
        )

    result = _serialize_historical_result(
        engine_result,
        provider=batch.meta.provider,
        retrieved_at=batch.meta.retrieved_at,
        requested_period_start=command.period_start,
        requested_period_end=command.period_end,
    )
    comparison = HistoricalRebalanceComparison(
        user=user,
        portfolio=portfolio,
        target_allocation=target,
        period_start=command.period_start,
        period_end=command.period_end,
        provider=batch.meta.provider,
        price_field="adjusted_close",
        retrieved_at=batch.meta.retrieved_at,
        drift_threshold=Decimal(str(command.drift_threshold)),
        commission_rate=Decimal(str(command.commission_rate)),
        slippage_rate=Decimal(str(command.slippage_rate)),
        engine_version=PORTFOLIO_ENGINE_VERSION,
        result=result,
        warnings=warnings,
    )
    comparison.full_clean()
    comparison.save()
    return comparison


def _owned_target_allocation(
    *,
    user: User,
    portfolio: Portfolio,
    target_allocation_id: UUID,
) -> TargetAllocation:
    target = (
        TargetAllocation.objects.filter(
            id=target_allocation_id,
            user=user,
            portfolio=portfolio,
        )
        .prefetch_related("weights__asset")
        .first()
    )
    if target is None:
        raise RebalancingApplicationError(
            "Target allocation not found for this portfolio.",
            code="TARGET_ALLOCATION_NOT_FOUND",
        )
    return target


def _engine_targets(target: TargetAllocation) -> tuple[TargetWeight, ...]:
    return tuple(
        TargetWeight(asset_id=weight.asset_id, weight=float(weight.weight))
        for weight in target.weights.all()
    )


def _serialize_historical_result(
    result: HistoricalRebalanceComparisonResult,
    *,
    provider: str,
    retrieved_at: datetime,
    requested_period_start: date,
    requested_period_end: date,
) -> dict[str, object]:
    return {
        "period_start": result.period_start.isoformat(),
        "period_end": result.period_end.isoformat(),
        "aligned_dates": [item.isoformat() for item in result.aligned_dates],
        "initial_state": {
            "cash": result.initial_cash,
            "positions": [
                {"asset_id": str(item.asset_id), "quantity": item.quantity}
                for item in result.initial_positions
            ],
        },
        "target_weights": [
            {
                "asset_id": str(item.asset_id) if item.asset_id is not None else None,
                "is_cash": item.asset_id is None,
                "weight": item.weight,
            }
            for item in result.target_weights
        ],
        "assumptions": {
            "price_field": "adjusted_close",
            "execution_timing": "decision_at_t_execute_at_next_aligned_observation",
            "commission_rate": result.commission_rate,
            "slippage_rate": result.slippage_rate,
            "turnover_convention": result.turnover_convention,
            "later_actual_ledger_activity": "ignored_after_initial_state",
        },
        "policies": [
            _serialize_policy_result(policy_result) for policy_result in result.policy_results
        ],
        "provenance": {
            "provider": provider,
            "retrieved_at": retrieved_at.isoformat(),
            "engine_version": PORTFOLIO_ENGINE_VERSION,
            "requested_period_start": requested_period_start.isoformat(),
            "requested_period_end": requested_period_end.isoformat(),
        },
    }


def _serialize_policy_result(
    result: HistoricalRebalancePolicyResult,
) -> dict[str, object]:
    policy = result.policy
    return {
        "name": policy.name,
        "schedule": policy.schedule.value if policy.schedule is not None else None,
        "threshold": policy.threshold,
        "summary": {
            "initial_value": result.initial_value,
            "ending_value": result.ending_value,
            "cumulative_return": result.cumulative_return,
            "rebalance_count": result.rebalance_count,
            "trade_count": result.trade_count,
            "maximum_absolute_drift": result.maximum_absolute_drift,
            "turnover": result.turnover,
            "commission_cost": result.commission_cost,
            "slippage_cost": result.slippage_cost,
            "total_cost": result.total_cost,
        },
        "snapshots": [
            {
                "trade_date": snapshot.trade_date.isoformat(),
                "total_value": snapshot.total_value,
                "cash_value": snapshot.cash_value,
                "period_return": snapshot.period_return,
                "lines": [
                    {
                        "asset_id": str(line.asset_id) if line.asset_id is not None else None,
                        "is_cash": line.asset_id is None,
                        "market_value": line.market_value,
                        "weight": line.weight,
                        "target_weight": line.target_weight,
                        "absolute_drift": line.absolute_drift,
                        "relative_drift": line.relative_drift,
                    }
                    for line in snapshot.lines
                ],
            }
            for snapshot in result.snapshots
        ],
        "events": [
            {
                "trigger": event.trigger.value,
                "decision_date": event.decision_date.isoformat(),
                "execution_date": event.execution_date.isoformat(),
                "pre_trade_value": event.pre_trade_value,
                "post_trade_value": event.post_trade_value,
                "turnover": event.turnover,
                "commission_cost": event.commission_cost,
                "slippage_cost": event.slippage_cost,
                "decision_lines": [
                    _serialize_rebalance_line(line) for line in event.decision_lines
                ],
                "trades": [
                    {
                        "asset_id": str(trade.asset_id),
                        "direction": trade.direction.value,
                        "quantity": trade.quantity,
                        "reference_price": trade.reference_price,
                        "fill_price": trade.fill_price,
                        "fill_notional": trade.fill_notional,
                        "commission_cost": trade.commission_cost,
                        "slippage_cost": trade.slippage_cost,
                    }
                    for trade in event.trades
                ],
            }
            for event in result.events
        ],
        "warnings": [_serialize_warning(warning) for warning in result.warnings],
    }


def _serialize_rebalance_line(line: RebalanceLine) -> dict[str, object]:
    return {
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


def _serialize_warning(warning: HistoricalRebalanceWarning) -> dict[str, str]:
    return {
        "code": warning.code.value,
        "message": warning.message,
    }
