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
    MarketBarQueryError,
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
from apps.portfolios.services.daily_performance import (
    DailyPerformanceError,
    DailyPortfolioPerformanceResult,
    calculate_owned_portfolio_daily_performance,
)
from apps.portfolios.services.ledger import LedgerReplayResult, replay_portfolio_ledger
from apps.rebalancing.models import (
    HistoricalRebalanceComparison,
    RebalanceSimulation,
    TargetAllocation,
    TargetAllocationWeight,
)
from portfolio_engine.config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.rebalancing import (
    REBALANCING_METHOD_VERSION,
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
    trading_calendar: TradingSessionCalendar,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> HistoricalRebalanceComparison:
    """Persist an annual/quarterly/threshold historical comparison.

    The initial simulated state is the authoritative owned-portfolio end-of-day
    ledger state on ``period_start``. Later real ledger activity is deliberately
    excluded from each hypothetical policy. The actual-portfolio baseline replays
    real ledger activity through the canonical daily TWR service over the exact
    aligned comparison period.
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
    initial_as_of = datetime.combine(command.period_start, time.max, tzinfo=UTC)
    end_exclusive = datetime.combine(command.period_end + timedelta(days=1), time.min, tzinfo=UTC)
    ledger = replay_portfolio_ledger(portfolio, as_of=initial_as_of)
    _validate_historical_initial_state(ledger)

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
                    "Hypothetical rebalancing policies start from the portfolio ledger state "
                    f"at {initial_as_of.isoformat()} and do not apply later real portfolio "
                    "transactions. The actual-portfolio TWR baseline does replay those "
                    "transactions."
                ),
            }
        )

    actual_portfolio, actual_warnings = _build_actual_portfolio_baseline(
        user=user,
        portfolio=portfolio,
        period_start=engine_result.period_start,
        period_end=engine_result.period_end,
        aligned_dates=engine_result.aligned_dates,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
    )
    warnings.extend(actual_warnings)

    result = _serialize_historical_result(
        engine_result,
        actual_portfolio=actual_portfolio,
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


def _validate_historical_initial_state(ledger: LedgerReplayResult) -> None:
    """Reject invalid historical starting states before market-data execution."""
    if ledger.cash_balance < Decimal("0"):
        raise RebalancingApplicationError(
            (
                "Historical comparison cannot start from a negative cash balance. "
                "Choose a later start date or correct the portfolio ledger."
            ),
            code="INVALID_INITIAL_PORTFOLIO_STATE",
        )

    has_positive_position = any(position.quantity > 0 for position in ledger.positions)
    if not has_positive_position and ledger.cash_balance <= Decimal("0"):
        raise RebalancingApplicationError(
            (
                "Historical comparison requires positive investable value at the requested "
                "period start. Choose a start date on or after the portfolio's first funded "
                "ledger state."
            ),
            code="INVALID_INITIAL_PORTFOLIO_STATE",
        )


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
    actual_portfolio: dict[str, object],
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
            "later_actual_ledger_activity": "ignored_by_hypothetical_policies",
            "actual_portfolio_return_method": "TIME_WEIGHTED",
            "actual_portfolio_series_basis": "normalized_growth_of_100_from_same_period_twr",
        },
        "actual_portfolio": actual_portfolio,
        "policies": [
            _serialize_policy_result(
                policy_result,
                actual_cumulative_return=_actual_cumulative_return(actual_portfolio),
            )
            for policy_result in result.policy_results
        ],
        "provenance": {
            "provider": provider,
            "retrieved_at": retrieved_at.isoformat(),
            "engine_version": PORTFOLIO_ENGINE_VERSION,
            "method_version": REBALANCING_METHOD_VERSION,
            "requested_period_start": requested_period_start.isoformat(),
            "requested_period_end": requested_period_end.isoformat(),
        },
    }


def _actual_cumulative_return(actual_portfolio: dict[str, object]) -> float | None:
    value = actual_portfolio.get("cumulative_return")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _serialize_policy_result(
    result: HistoricalRebalancePolicyResult,
    *,
    actual_cumulative_return: float | None,
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
            "growth_of_100_ending": _growth_of_100(result.cumulative_return),
            "return_difference_pp_vs_actual": _return_difference_pp_vs_actual(
                result.cumulative_return,
                actual_cumulative_return,
            ),
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
                "growth_of_100": _normalized_policy_growth_of_100(
                    snapshot.total_value,
                    result.initial_value,
                ),
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


def _build_actual_portfolio_baseline(
    *,
    user: User,
    portfolio: Portfolio,
    period_start: date,
    period_end: date,
    aligned_dates: tuple[date, ...],
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    executor: MarketBarQueryExecutor,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    """Build actual owned-portfolio TWR over the exact aligned comparison period.

    The canonical daily-performance service receives every trading session between
    the simulation's aligned start and end dates. The persisted chart series is
    then sampled only on the simulation-aligned dates so the actual and
    hypothetical paths share the same x-axis without weakening daily TWR cash-flow
    semantics.
    """
    try:
        valuation_times = _actual_performance_valuation_times(
            period_start=period_start,
            period_end=period_end,
            trading_calendar=trading_calendar,
        )
        performance = calculate_owned_portfolio_daily_performance(
            user=user,
            portfolio_id=portfolio.id,
            valuation_times=valuation_times,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            executor=executor,
        )
    except (DailyPerformanceError, MarketBarQueryError) as exc:
        message = (
            "Actual portfolio performance is unavailable for the exact aligned "
            f"comparison period: {exc}"
        )
        warning = {
            "code": "ACTUAL_PORTFOLIO_COMPARISON_UNAVAILABLE",
            "message": message,
        }
        return (
            _unavailable_actual_portfolio(
                period_start=period_start,
                period_end=period_end,
                provider=provider_name,
                message=message,
            ),
            [warning],
        )

    if performance.twr is None:
        detail = next(
            (
                warning.message
                for warning in performance.warnings
                if warning.code.value == "TWR_UNDEFINED"
            ),
            "daily TWR is undefined for the aligned comparison period.",
        )
        message = (
            f"Actual portfolio performance is unavailable for an exact comparison because {detail}"
        )
        warning = {
            "code": "ACTUAL_PORTFOLIO_COMPARISON_UNAVAILABLE",
            "message": message,
        }
        return (
            _unavailable_actual_portfolio(
                period_start=period_start,
                period_end=period_end,
                provider=performance.provenance.provider,
                message=message,
                performance=performance,
            ),
            [warning],
        )

    raw_values = {
        valuation.as_of.date(): (
            float(valuation.total_value) if valuation.total_value is not None else None
        )
        for valuation in performance.valuations
    }
    cumulative_returns: dict[date, float] = {performance.twr.period_start: 0.0}
    growth_factor = 1.0
    for observation in performance.twr.daily_returns:
        growth_factor *= 1.0 + observation.simple_return
        cumulative_returns[observation.valuation_date] = growth_factor - 1.0

    series: list[dict[str, object]] = []
    for trade_date in aligned_dates:
        cumulative_return = cumulative_returns.get(trade_date)
        portfolio_value = raw_values.get(trade_date)
        if cumulative_return is None or portfolio_value is None:
            message = (
                "Actual portfolio performance is unavailable for an exact comparison "
                f"because the aligned date {trade_date.isoformat()} lacks a complete "
                "daily valuation/TWR observation."
            )
            warning = {
                "code": "ACTUAL_PORTFOLIO_COMPARISON_UNAVAILABLE",
                "message": message,
            }
            return (
                _unavailable_actual_portfolio(
                    period_start=period_start,
                    period_end=period_end,
                    provider=performance.provenance.provider,
                    message=message,
                    performance=performance,
                ),
                [warning],
            )
        series.append(
            {
                "trade_date": trade_date.isoformat(),
                "portfolio_value": portfolio_value,
                "cumulative_return": cumulative_return,
                "growth_of_100": _growth_of_100(cumulative_return),
            }
        )

    starting_value = raw_values.get(performance.twr.period_start)
    ending_value = raw_values.get(performance.twr.period_end)
    return (
        {
            "available": True,
            "return_method": "TIME_WEIGHTED",
            "period_start": performance.twr.period_start.isoformat(),
            "period_end": performance.twr.period_end.isoformat(),
            "starting_portfolio_value": starting_value,
            "ending_portfolio_value": ending_value,
            "cumulative_return": performance.twr.cumulative_return,
            "growth_of_100_start": 100.0,
            "growth_of_100_end": _growth_of_100(performance.twr.cumulative_return),
            "series": series,
            "provenance": {
                "provider": performance.provenance.provider,
                "retrieved_at": (
                    performance.provenance.retrieved_at.isoformat()
                    if performance.provenance.retrieved_at is not None
                    else None
                ),
                "price_field": performance.provenance.price_field,
            },
            "warnings": _serialize_actual_performance_warnings(performance),
        },
        [],
    )


def _actual_performance_valuation_times(
    *,
    period_start: date,
    period_end: date,
    trading_calendar: TradingSessionCalendar,
) -> tuple[datetime, ...]:
    if period_start >= period_end:
        raise DailyPerformanceError(
            "actual portfolio comparison period must contain at least two dates"
        )

    calendar_days = (period_end - period_start).days
    sessions = trading_calendar.sessions_through(
        period_end,
        count=calendar_days + 1,
    )
    selected = tuple(session for session in sessions if period_start <= session <= period_end)
    if len(selected) < 2:
        raise DailyPerformanceError(
            "actual portfolio comparison period must contain at least two trading sessions"
        )
    if selected[0] != period_start or selected[-1] != period_end:
        raise DailyPerformanceError(
            "actual portfolio comparison endpoints must be trading sessions"
        )
    return tuple(datetime.combine(session, time.max, tzinfo=UTC) for session in selected)


def _unavailable_actual_portfolio(
    *,
    period_start: date,
    period_end: date,
    provider: str,
    message: str,
    performance: DailyPortfolioPerformanceResult | None = None,
) -> dict[str, object]:
    return {
        "available": False,
        "return_method": "TIME_WEIGHTED",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "starting_portfolio_value": None,
        "ending_portfolio_value": None,
        "cumulative_return": None,
        "growth_of_100_start": None,
        "growth_of_100_end": None,
        "series": [],
        "provenance": {
            "provider": (performance.provenance.provider if performance is not None else provider),
            "retrieved_at": (
                performance.provenance.retrieved_at.isoformat()
                if performance is not None and performance.provenance.retrieved_at is not None
                else None
            ),
            "price_field": (
                performance.provenance.price_field if performance is not None else "adjusted_close"
            ),
        },
        "warnings": [
            *_serialize_actual_performance_warnings(performance),
            {
                "code": "ACTUAL_PORTFOLIO_COMPARISON_UNAVAILABLE",
                "message": message,
            },
        ],
    }


def _serialize_actual_performance_warnings(
    performance: DailyPortfolioPerformanceResult | None,
) -> list[dict[str, str]]:
    if performance is None:
        return []

    serialized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for warning in performance.warnings:
        item = (warning.code.value, warning.message)
        if item in seen:
            continue
        seen.add(item)
        serialized.append(
            {
                "code": warning.code.value,
                "message": warning.message,
            }
        )
    return serialized


def _growth_of_100(cumulative_return: float) -> float:
    return 100.0 * (1.0 + cumulative_return)


def _normalized_policy_growth_of_100(
    portfolio_value: float,
    initial_value: float,
) -> float:
    if initial_value <= 0.0:
        raise RebalancingApplicationError(
            "Historical policy initial value must be positive for normalized growth."
        )
    return 100.0 * portfolio_value / initial_value


def _return_difference_pp_vs_actual(
    simulated_cumulative_return: float,
    actual_cumulative_return: float | None,
) -> float | None:
    """Return simulated minus actual same-period cumulative return in percentage points."""
    if actual_cumulative_return is None:
        return None
    return (simulated_cumulative_return - actual_cumulative_return) * 100.0


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
