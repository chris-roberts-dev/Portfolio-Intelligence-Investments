"""Deterministic historical rebalancing comparison for Phase 5.

Development guide references: Sections 9.6-9.7, 13, 14.3, 14.5-14.6,
17.1, 19.6, 23.6, and 27.

This module deliberately implements only the state evolution required to compare
schedule and drift-threshold rebalancing policies. It is not a general strategy
or backtesting interface. Decisions use prices observable on date ``t`` and any
resulting rebalance executes on the next common market date using that date's
adjusted-close reference price.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import NoReturn
from uuid import UUID

from portfolio_engine.config import (
    DEFAULT_COMMISSION_RATE,
    DEFAULT_SLIPPAGE_RATE,
    WEIGHT_SUM_TOLERANCE,
)
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.rebalancing.contracts import (
    CurrentValue,
    HistoricalAllocationLine,
    HistoricalPortfolioSnapshot,
    HistoricalPosition,
    HistoricalRebalanceComparisonResult,
    HistoricalRebalanceEvent,
    HistoricalRebalancePolicy,
    HistoricalRebalancePolicyResult,
    HistoricalRebalanceTrade,
    HistoricalRebalanceTrigger,
    HistoricalRebalanceWarning,
    HistoricalRebalanceWarningCode,
    RebalanceLine,
    RebalancingError,
    RebalancingErrorCode,
    SimulatedTradeDirection,
    TargetWeight,
)
from portfolio_engine.rebalancing.core import simulate_rebalance, validate_target_weights
from portfolio_engine.rebalancing.rules import (
    scheduled_rebalance_due,
    threshold_rebalance_triggered,
)

TURNOVER_CONVENTION = "gross executed fill notional / pre-trade portfolio value"


@dataclass(slots=True)
class _MutablePortfolioState:
    quantities: dict[UUID, float]
    cash: float


@dataclass(frozen=True, slots=True)
class _PendingDecision:
    trigger: HistoricalRebalanceTrigger
    decision_date: date
    decision_lines: tuple[RebalanceLine, ...]


def compare_historical_rebalancing(
    *,
    price_frames: Mapping[UUID, PriceFrame],
    initial_positions: Sequence[HistoricalPosition],
    initial_cash: float,
    targets: Sequence[TargetWeight],
    policies: Sequence[HistoricalRebalancePolicy],
    commission_rate: float = DEFAULT_COMMISSION_RATE,
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
) -> HistoricalRebalanceComparisonResult:
    """Compare deterministic schedule/threshold policies over adjusted-close history.

    Every required security must provide positive finite ``adjusted_close`` values.
    Dates are aligned by explicit complete-case intersection across all securities;
    missing dates are never forward-filled or converted to zero. A rebalance decision
    observed on ``t`` is represented as a target-allocation intent and may execute only
    on the next aligned date.
    """
    normalized_targets = validate_target_weights(targets)
    normalized_positions = _validate_initial_positions(initial_positions)
    normalized_cash = _finite_nonnegative(initial_cash, "initial_cash")
    normalized_commission = _unit_rate(commission_rate, "commission_rate")
    normalized_slippage = _unit_rate(slippage_rate, "slippage_rate")
    normalized_policies = _validate_policies(policies)

    required_asset_ids = _required_asset_ids(normalized_positions, normalized_targets)
    aligned_dates, prices_by_asset, warnings = _align_adjusted_close_history(
        price_frames,
        required_asset_ids=required_asset_ids,
    )

    policy_results = tuple(
        _simulate_policy(
            aligned_dates=aligned_dates,
            prices_by_asset=prices_by_asset,
            initial_positions=normalized_positions,
            initial_cash=normalized_cash,
            targets=normalized_targets,
            policy=policy,
            commission_rate=normalized_commission,
            slippage_rate=normalized_slippage,
        )
        for policy in normalized_policies
    )

    return HistoricalRebalanceComparisonResult(
        period_start=aligned_dates[0],
        period_end=aligned_dates[-1],
        aligned_dates=aligned_dates,
        target_weights=normalized_targets,
        initial_positions=normalized_positions,
        initial_cash=normalized_cash,
        commission_rate=normalized_commission,
        slippage_rate=normalized_slippage,
        turnover_convention=TURNOVER_CONVENTION,
        policy_results=policy_results,
        warnings=warnings,
    )


def _simulate_policy(
    *,
    aligned_dates: tuple[date, ...],
    prices_by_asset: dict[UUID, dict[date, float]],
    initial_positions: tuple[HistoricalPosition, ...],
    initial_cash: float,
    targets: tuple[TargetWeight, ...],
    policy: HistoricalRebalancePolicy,
    commission_rate: float,
    slippage_rate: float,
) -> HistoricalRebalancePolicyResult:
    state = _MutablePortfolioState(
        quantities={position.asset_id: position.quantity for position in initial_positions},
        cash=initial_cash,
    )
    target_asset_ids = tuple(target.asset_id for target in targets if target.asset_id is not None)
    for asset_id in target_asset_ids:
        state.quantities.setdefault(asset_id, 0.0)

    snapshots: list[HistoricalPortfolioSnapshot] = []
    events: list[HistoricalRebalanceEvent] = []
    warnings: list[HistoricalRebalanceWarning] = []
    pending: _PendingDecision | None = None
    previous_rebalance_date: date | None = None

    for index, trade_date in enumerate(aligned_dates):
        prices = {asset_id: history[trade_date] for asset_id, history in prices_by_asset.items()}

        if pending is not None:
            event = _execute_target_rebalance(
                state=state,
                prices=prices,
                targets=targets,
                pending=pending,
                execution_date=trade_date,
                commission_rate=commission_rate,
                slippage_rate=slippage_rate,
            )
            events.append(event)
            previous_rebalance_date = pending.decision_date
            pending = None

        snapshot, decision_lines = _snapshot_and_lines(
            trade_date=trade_date,
            state=state,
            prices=prices,
            targets=targets,
            previous_total_value=(snapshots[-1].total_value if snapshots else None),
        )
        snapshots.append(snapshot)

        trigger = _decision_trigger(
            policy=policy,
            lines=decision_lines,
            decision_date=trade_date,
            previous_rebalance_date=previous_rebalance_date,
        )
        if trigger is None:
            continue

        if index == len(aligned_dates) - 1:
            warnings.append(
                HistoricalRebalanceWarning(
                    code=HistoricalRebalanceWarningCode.UNEXECUTED_FINAL_DECISION,
                    message=(
                        f"{policy.name} generated a rebalance decision on {trade_date.isoformat()} "
                        "but no later aligned observation was available for execution."
                    ),
                )
            )
            continue

        pending = _PendingDecision(
            trigger=trigger,
            decision_date=trade_date,
            decision_lines=decision_lines,
        )

    initial_value = snapshots[0].total_value
    ending_value = snapshots[-1].total_value
    cumulative_return = ending_value / initial_value - 1.0
    commission_cost = math.fsum(event.commission_cost for event in events)
    slippage_cost = math.fsum(event.slippage_cost for event in events)

    return HistoricalRebalancePolicyResult(
        policy=policy,
        snapshots=tuple(snapshots),
        events=tuple(events),
        initial_value=initial_value,
        ending_value=ending_value,
        cumulative_return=cumulative_return,
        rebalance_count=len(events),
        trade_count=sum(len(event.trades) for event in events),
        maximum_absolute_drift=max(
            abs(line.absolute_drift) for snapshot in snapshots for line in snapshot.lines
        ),
        turnover=math.fsum(event.turnover for event in events),
        commission_cost=commission_cost,
        slippage_cost=slippage_cost,
        total_cost=commission_cost + slippage_cost,
        warnings=tuple(warnings),
    )


def _decision_trigger(
    *,
    policy: HistoricalRebalancePolicy,
    lines: tuple[RebalanceLine, ...],
    decision_date: date,
    previous_rebalance_date: date | None,
) -> HistoricalRebalanceTrigger | None:
    if policy.schedule is not None:
        if scheduled_rebalance_due(
            schedule=policy.schedule,
            decision_date=decision_date,
            previous_rebalance_date=previous_rebalance_date,
        ):
            return HistoricalRebalanceTrigger.SCHEDULE
        return None

    if policy.threshold is None:
        _raise(RebalancingErrorCode.INVALID_INPUT, "Historical policy is missing its rule.")

    if threshold_rebalance_triggered(lines, threshold=policy.threshold):
        return HistoricalRebalanceTrigger.THRESHOLD

    return None


def _snapshot_and_lines(
    *,
    trade_date: date,
    state: _MutablePortfolioState,
    prices: Mapping[UUID, float],
    targets: tuple[TargetWeight, ...],
    previous_total_value: float | None,
) -> tuple[HistoricalPortfolioSnapshot, tuple[RebalanceLine, ...]]:
    current_values = tuple(
        CurrentValue(
            asset_id=asset_id,
            market_value=quantity * prices[asset_id],
        )
        for asset_id, quantity in sorted(state.quantities.items(), key=lambda item: str(item[0]))
        if quantity > WEIGHT_SUM_TOLERANCE
    ) + (CurrentValue(asset_id=None, market_value=state.cash),)

    simulation = simulate_rebalance(current_values, targets)
    allocation_lines = tuple(
        HistoricalAllocationLine(
            asset_id=line.asset_id,
            market_value=line.current_value,
            weight=line.current_weight,
            target_weight=line.target_weight,
            absolute_drift=line.absolute_drift,
            relative_drift=line.relative_drift,
        )
        for line in simulation.lines
    )
    return (
        HistoricalPortfolioSnapshot(
            trade_date=trade_date,
            total_value=simulation.total_investable_value,
            cash_value=state.cash,
            period_return=(
                None
                if previous_total_value is None
                else simulation.total_investable_value / previous_total_value - 1.0
            ),
            lines=allocation_lines,
        ),
        simulation.lines,
    )


def _execute_target_rebalance(
    *,
    state: _MutablePortfolioState,
    prices: Mapping[UUID, float],
    targets: tuple[TargetWeight, ...],
    pending: _PendingDecision,
    execution_date: date,
    commission_rate: float,
    slippage_rate: float,
) -> HistoricalRebalanceEvent:
    current_values = tuple(
        CurrentValue(asset_id=asset_id, market_value=quantity * prices[asset_id])
        for asset_id, quantity in sorted(state.quantities.items(), key=lambda item: str(item[0]))
        if quantity > WEIGHT_SUM_TOLERANCE
    ) + (CurrentValue(asset_id=None, market_value=state.cash),)
    simulation = simulate_rebalance(current_values, targets)
    pre_trade_value = simulation.total_investable_value
    target_by_asset = {
        target.asset_id: target.weight for target in targets if target.asset_id is not None
    }

    desired_deltas: dict[UUID, float] = {}
    for asset_id in prices:
        current_quantity = state.quantities.get(asset_id, 0.0)
        target_value = pre_trade_value * target_by_asset.get(asset_id, 0.0)
        target_quantity = target_value / prices[asset_id]
        desired_deltas[asset_id] = target_quantity - current_quantity

    trades: list[HistoricalRebalanceTrade] = []

    for asset_id in sorted(desired_deltas, key=str):
        delta = desired_deltas[asset_id]
        if delta >= -WEIGHT_SUM_TOLERANCE:
            continue
        quantity = min(state.quantities.get(asset_id, 0.0), -delta)
        if quantity <= WEIGHT_SUM_TOLERANCE:
            continue
        trade = _fill_trade(
            asset_id=asset_id,
            direction=SimulatedTradeDirection.SELL,
            quantity=quantity,
            reference_price=prices[asset_id],
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        state.quantities[asset_id] = max(0.0, state.quantities.get(asset_id, 0.0) - quantity)
        state.cash += trade.fill_notional - trade.commission_cost
        trades.append(trade)

    buy_requests = [
        (asset_id, delta)
        for asset_id, delta in sorted(desired_deltas.items(), key=lambda item: str(item[0]))
        if delta > WEIGHT_SUM_TOLERANCE
    ]
    requested_buy_cost = math.fsum(
        _buy_cash_cost(
            quantity=quantity,
            reference_price=prices[asset_id],
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        for asset_id, quantity in buy_requests
    )
    scale = 1.0
    if requested_buy_cost > state.cash and requested_buy_cost > 0.0:
        scale = max(0.0, state.cash / requested_buy_cost)

    for asset_id, requested_quantity in buy_requests:
        quantity = requested_quantity * scale
        if quantity <= WEIGHT_SUM_TOLERANCE:
            continue
        trade = _fill_trade(
            asset_id=asset_id,
            direction=SimulatedTradeDirection.BUY,
            quantity=quantity,
            reference_price=prices[asset_id],
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        cash_cost = trade.fill_notional + trade.commission_cost
        if cash_cost > state.cash and cash_cost - state.cash <= WEIGHT_SUM_TOLERANCE:
            cash_cost = state.cash
        if cash_cost > state.cash + WEIGHT_SUM_TOLERANCE:
            _raise(
                RebalancingErrorCode.NEGATIVE_CASH,
                "Scaled historical rebalance buy would create negative cash.",
            )
        state.cash -= cash_cost
        state.quantities[asset_id] = state.quantities.get(asset_id, 0.0) + quantity
        trades.append(trade)

    if state.cash < -WEIGHT_SUM_TOLERANCE:
        _raise(
            RebalancingErrorCode.NEGATIVE_CASH,
            "Historical rebalance execution created negative cash.",
        )
    if state.cash < 0.0:
        state.cash = 0.0

    post_trade_value = state.cash + math.fsum(
        quantity * prices[asset_id] for asset_id, quantity in state.quantities.items()
    )
    commission_cost = math.fsum(trade.commission_cost for trade in trades)
    slippage_cost = math.fsum(trade.slippage_cost for trade in trades)
    gross_fill_notional = math.fsum(trade.fill_notional for trade in trades)
    turnover = 0.0 if pre_trade_value <= 0.0 else gross_fill_notional / pre_trade_value

    return HistoricalRebalanceEvent(
        trigger=pending.trigger,
        decision_date=pending.decision_date,
        execution_date=execution_date,
        decision_lines=pending.decision_lines,
        pre_trade_value=pre_trade_value,
        post_trade_value=post_trade_value,
        turnover=turnover,
        commission_cost=commission_cost,
        slippage_cost=slippage_cost,
        trades=tuple(trades),
    )


def _fill_trade(
    *,
    asset_id: UUID,
    direction: SimulatedTradeDirection,
    quantity: float,
    reference_price: float,
    commission_rate: float,
    slippage_rate: float,
) -> HistoricalRebalanceTrade:
    if direction is SimulatedTradeDirection.BUY:
        fill_price = reference_price * (1.0 + slippage_rate)
    elif direction is SimulatedTradeDirection.SELL:
        fill_price = reference_price * (1.0 - slippage_rate)
    else:
        _raise(RebalancingErrorCode.INVALID_INPUT, "Historical fill direction must be BUY or SELL.")

    fill_notional = quantity * fill_price
    commission_cost = fill_notional * commission_rate
    slippage_cost = quantity * abs(fill_price - reference_price)
    return HistoricalRebalanceTrade(
        asset_id=asset_id,
        direction=direction,
        quantity=quantity,
        reference_price=reference_price,
        fill_price=fill_price,
        fill_notional=fill_notional,
        commission_cost=commission_cost,
        slippage_cost=slippage_cost,
    )


def _buy_cash_cost(
    *,
    quantity: float,
    reference_price: float,
    commission_rate: float,
    slippage_rate: float,
) -> float:
    fill_price = reference_price * (1.0 + slippage_rate)
    fill_notional = quantity * fill_price
    return fill_notional * (1.0 + commission_rate)


def _align_adjusted_close_history(
    price_frames: Mapping[UUID, PriceFrame],
    *,
    required_asset_ids: tuple[UUID, ...],
) -> tuple[
    tuple[date, ...],
    dict[UUID, dict[date, float]],
    tuple[HistoricalRebalanceWarning, ...],
]:
    if not required_asset_ids:
        _raise(
            RebalancingErrorCode.INVALID_PRICE_HISTORY,
            "Historical comparison requires at least one security asset.",
        )

    prices_by_asset: dict[UUID, dict[date, float]] = {}
    date_sets: list[set[date]] = []
    union_dates: set[date] = set()

    for asset_id in required_asset_ids:
        frame = price_frames.get(asset_id)
        if not frame:
            _raise(
                RebalancingErrorCode.INVALID_PRICE_HISTORY,
                f"Missing historical price frame for asset {asset_id}.",
            )

        price_by_date: dict[date, float] = {}
        previous_date: date | None = None
        for bar in frame:
            if bar.asset_id != asset_id:
                _raise(
                    RebalancingErrorCode.INVALID_PRICE_HISTORY,
                    f"Price frame for asset {asset_id} contains another asset identity.",
                )
            if previous_date is not None and bar.trade_date <= previous_date:
                _raise(
                    RebalancingErrorCode.INVALID_PRICE_HISTORY,
                    f"Price frame for asset {asset_id} must be strictly ascending and unique.",
                )
            previous_date = bar.trade_date
            if bar.adjusted_close is None:
                continue
            price = _finite_positive(
                bar.adjusted_close,
                f"adjusted_close[{asset_id}][{bar.trade_date.isoformat()}]",
            )
            price_by_date[bar.trade_date] = price

        if not price_by_date:
            _raise(
                RebalancingErrorCode.INVALID_PRICE_HISTORY,
                f"Asset {asset_id} has no usable adjusted-close observations.",
            )
        prices_by_asset[asset_id] = price_by_date
        dates = set(price_by_date)
        date_sets.append(dates)
        union_dates.update(dates)

    common_dates = set(date_sets[0])
    common_dates.intersection_update(*date_sets[1:])
    aligned_dates = tuple(sorted(common_dates))
    if len(aligned_dates) < 2:
        _raise(
            RebalancingErrorCode.INSUFFICIENT_HISTORY,
            "Historical comparison requires at least two common adjusted-close observations.",
        )

    warnings: tuple[HistoricalRebalanceWarning, ...] = ()
    if len(common_dates) != len(union_dates):
        warnings = (
            HistoricalRebalanceWarning(
                code=HistoricalRebalanceWarningCode.INCOMPLETE_DATE_INTERSECTION,
                message=(
                    "Historical comparison used the complete-case intersection of adjusted-close "
                    "dates; observations missing from any required asset were excluded without "
                    "forward-filling."
                ),
            ),
        )
    return aligned_dates, prices_by_asset, warnings


def _required_asset_ids(
    initial_positions: tuple[HistoricalPosition, ...],
    targets: tuple[TargetWeight, ...],
) -> tuple[UUID, ...]:
    asset_ids = {position.asset_id for position in initial_positions}
    asset_ids.update(target.asset_id for target in targets if target.asset_id is not None)
    return tuple(sorted(asset_ids, key=str))


def _validate_initial_positions(
    positions: Sequence[HistoricalPosition],
) -> tuple[HistoricalPosition, ...]:
    seen: set[UUID] = set()
    normalized: list[HistoricalPosition] = []
    for index, position in enumerate(positions):
        if position.asset_id in seen:
            _raise(
                RebalancingErrorCode.INVALID_INPUT,
                f"Duplicate initial position asset at index {index}.",
            )
        seen.add(position.asset_id)
        quantity = _finite_nonnegative(position.quantity, f"initial_positions[{index}].quantity")
        if quantity <= WEIGHT_SUM_TOLERANCE:
            continue
        normalized.append(HistoricalPosition(asset_id=position.asset_id, quantity=quantity))
    return tuple(normalized)


def _validate_policies(
    policies: Sequence[HistoricalRebalancePolicy],
) -> tuple[HistoricalRebalancePolicy, ...]:
    if not policies:
        _raise(RebalancingErrorCode.INVALID_INPUT, "At least one historical policy is required.")

    names: set[str] = set()
    normalized: list[HistoricalRebalancePolicy] = []
    for index, policy in enumerate(policies):
        name = policy.name.strip()
        if not name:
            _raise(RebalancingErrorCode.INVALID_INPUT, f"policies[{index}].name must not be blank.")
        if name in names:
            _raise(
                RebalancingErrorCode.INVALID_INPUT,
                f"Duplicate historical policy name {name!r}.",
            )
        names.add(name)

        if (policy.schedule is None) == (policy.threshold is None):
            _raise(
                RebalancingErrorCode.INVALID_INPUT,
                f"Policy {name!r} must define exactly one schedule or threshold rule.",
            )
        threshold = None
        if policy.threshold is not None:
            threshold = _unit_interval(
                policy.threshold,
                f"policies[{index}].threshold",
                error_code=RebalancingErrorCode.INVALID_INPUT,
            )
        normalized.append(
            HistoricalRebalancePolicy(
                name=name,
                schedule=policy.schedule,
                threshold=threshold,
            )
        )
    return tuple(normalized)


def _unit_rate(value: object, field_name: str) -> float:
    return _unit_interval(
        value,
        field_name,
        error_code=RebalancingErrorCode.INVALID_COST_ASSUMPTION,
    )


def _unit_interval(
    value: object,
    field_name: str,
    *,
    error_code: RebalancingErrorCode,
) -> float:
    number = _finite(value, field_name)
    if number < 0.0 or number > 1.0:
        _raise(
            error_code,
            f"{field_name} must be between zero and one.",
        )
    return number


def _finite_positive(value: object, field_name: str) -> float:
    number = _finite(value, field_name)
    if number <= 0.0:
        _raise(RebalancingErrorCode.INVALID_PRICE_HISTORY, f"{field_name} must be positive.")
    return number


def _finite_nonnegative(value: object, field_name: str) -> float:
    number = _finite(value, field_name)
    if number < 0.0:
        _raise(RebalancingErrorCode.INVALID_INPUT, f"{field_name} must not be negative.")
    return number


def _finite(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise(RebalancingErrorCode.INVALID_INPUT, f"{field_name} must be a real number.")
    number = float(value)
    if not math.isfinite(number):
        _raise(RebalancingErrorCode.INVALID_INPUT, f"{field_name} must be finite.")
    return number


def _raise(code: RebalancingErrorCode, message: str) -> NoReturn:
    raise RebalancingError(code, message)
