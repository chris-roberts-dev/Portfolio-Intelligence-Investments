"""Deterministic strategy-agnostic Phase 6 backtesting engine.

Development guide references: Sections 9.6-9.7, 14, 17.1-17.2, 19.4,
19.6, 20.2-20.3, 23.7, and 27.

This foundation deliberately stops at the generic execution/state boundary. It
does not implement buy-and-hold, moving-average, momentum, strategy discovery,
persistence, Django orchestration, or frontend behavior.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date
from typing import NoReturn
from uuid import UUID

from portfolio_engine.backtesting.context import BacktestStrategy, build_strategy_context
from portfolio_engine.backtesting.contracts import (
    BACKTEST_METHOD_VERSION,
    BacktestAssumptions,
    BacktestCostObservation,
    BacktestDataProvenance,
    BacktestDecision,
    BacktestEquityObservation,
    BacktestError,
    BacktestErrorCode,
    BacktestExecutionEvent,
    BacktestInitialPosition,
    BacktestProvenance,
    BacktestResult,
    BacktestReturnObservation,
    BacktestWarning,
    BacktestWarningCode,
    PortfolioState,
)
from portfolio_engine.backtesting.execution import execute_orders, normalize_orders
from portfolio_engine.backtesting.state import (
    build_initial_ledger_state,
    finite_unit_rate,
    value_portfolio_state,
)
from portfolio_engine.config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION

EXECUTION_TIMING = "decision_at_t_execute_at_next_aligned_observation"
TURNOVER_CONVENTION = "gross executed fill notional / pre-trade portfolio value"


def run_backtest(
    *,
    price_frames: Mapping[UUID, PriceFrame],
    initial_positions: Sequence[BacktestInitialPosition],
    initial_cash: float,
    strategy: BacktestStrategy,
    requested_period_start: date,
    requested_period_end_exclusive: date,
    data_provenance: BacktestDataProvenance,
    commission_rate: float = DEFAULT_COMMISSION_RATE,
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE,
) -> BacktestResult:
    """Run one deterministic daily-bar strategy simulation."""
    if requested_period_start >= requested_period_end_exclusive:
        _raise(
            BacktestErrorCode.INVALID_INPUT,
            "requested_period_start must be earlier than requested_period_end_exclusive.",
        )

    normalized_commission = finite_unit_rate(commission_rate, "commission_rate")
    normalized_slippage = finite_unit_rate(slippage_rate, "slippage_rate")
    strategy_name = _nonblank(strategy.name, "strategy.name")
    strategy_version = _nonblank(strategy.version, "strategy.version")
    minimum_history = _minimum_history(strategy.minimum_history_observations)
    provider = _nonblank(data_provenance.provider, "data_provenance.provider")

    (
        aligned_dates,
        prices_by_asset,
        usable_frames,
        alignment_warnings,
    ) = _prepare_price_history(
        price_frames,
        requested_period_start=requested_period_start,
        requested_period_end_exclusive=requested_period_end_exclusive,
    )
    asset_universe = frozenset(prices_by_asset)
    ledger = build_initial_ledger_state(
        positions=initial_positions,
        cash=initial_cash,
        asset_universe=asset_universe,
    )

    snapshots: list[PortfolioState] = []
    equity_curve: list[BacktestEquityObservation] = []
    returns: list[BacktestReturnObservation] = []
    decisions: list[BacktestDecision] = []
    executions: list[BacktestExecutionEvent] = []
    costs: list[BacktestCostObservation] = []
    warnings = list(alignment_warnings)
    pending: BacktestDecision | None = None
    previous_value: float | None = None

    common_history_dates = _common_history_dates(usable_frames)

    for index, trade_date in enumerate(aligned_dates):
        prices = {asset_id: values[trade_date] for asset_id, values in prices_by_asset.items()}

        if pending is not None:
            ledger, event, execution_warnings = execute_orders(
                ledger=ledger,
                orders=pending.orders,
                prices=prices,
                decision_date=pending.decision_date,
                execution_date=trade_date,
                commission_rate=normalized_commission,
                slippage_rate=normalized_slippage,
            )
            executions.append(event)
            warnings.extend(execution_warnings)
            costs.append(
                BacktestCostObservation(
                    execution_date=trade_date,
                    commission_cost=event.commission_cost,
                    slippage_cost=event.slippage_cost,
                    total_cost=event.total_cost,
                )
            )
            pending = None

        snapshot = value_portfolio_state(as_of=trade_date, ledger=ledger, prices=prices)
        snapshots.append(snapshot)
        equity_curve.append(
            BacktestEquityObservation(
                trade_date=trade_date,
                portfolio_value=snapshot.total_value,
            )
        )
        if previous_value is not None:
            returns.append(
                BacktestReturnObservation(
                    trade_date=trade_date,
                    simple_return=snapshot.total_value / previous_value - 1.0,
                )
            )
        previous_value = snapshot.total_value

        observation_count = sum(1 for value in common_history_dates if value <= trade_date)
        if observation_count < minimum_history:
            continue

        context = build_strategy_context(
            as_of=trade_date,
            usable_frames=usable_frames,
            portfolio=snapshot,
            observation_count=observation_count,
        )
        orders = normalize_orders(
            tuple(strategy.generate_orders(context)),
            asset_universe=asset_universe,
        )
        if not orders:
            continue

        decision = BacktestDecision(decision_date=trade_date, orders=orders)
        decisions.append(decision)
        if index == len(aligned_dates) - 1:
            warnings.append(
                BacktestWarning(
                    code=BacktestWarningCode.UNEXECUTED_FINAL_ORDERS,
                    message=(
                        f"Strategy generated {len(orders)} order(s) on {trade_date.isoformat()} "
                        "but no later aligned observation was available for execution."
                    ),
                )
            )
            continue
        pending = decision

    initial_value = snapshots[0].total_value
    ending_value = snapshots[-1].total_value
    commission = math.fsum(event.commission_cost for event in executions)
    slippage = math.fsum(event.slippage_cost for event in executions)

    return BacktestResult(
        aligned_dates=aligned_dates,
        snapshots=tuple(snapshots),
        equity_curve=tuple(equity_curve),
        returns=tuple(returns),
        decisions=tuple(decisions),
        executions=tuple(executions),
        costs=tuple(costs),
        initial_value=initial_value,
        ending_value=ending_value,
        cumulative_return=ending_value / initial_value - 1.0,
        trade_count=sum(len(event.fills) for event in executions),
        turnover=math.fsum(event.turnover for event in executions),
        commission_cost=commission,
        slippage_cost=slippage,
        total_cost=commission + slippage,
        assumptions=BacktestAssumptions(
            price_field="adjusted_close",
            execution_timing=EXECUTION_TIMING,
            commission_rate=normalized_commission,
            slippage_rate=normalized_slippage,
            turnover_convention=TURNOVER_CONVENTION,
            fractional_shares=True,
            long_only=True,
            leverage=False,
        ),
        provenance=BacktestProvenance(
            provider=provider,
            retrieved_at=data_provenance.retrieved_at,
            data_fingerprint=data_provenance.data_fingerprint,
            requested_period_start=requested_period_start,
            requested_period_end_exclusive=requested_period_end_exclusive,
            aligned_period_start=aligned_dates[0],
            aligned_period_end=aligned_dates[-1],
            engine_version=PORTFOLIO_ENGINE_VERSION,
            backtest_method_version=BACKTEST_METHOD_VERSION,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
        ),
        warnings=tuple(warnings),
    )


def _prepare_price_history(
    price_frames: Mapping[UUID, PriceFrame],
    *,
    requested_period_start: date,
    requested_period_end_exclusive: date,
) -> tuple[
    tuple[date, ...],
    dict[UUID, dict[date, float]],
    dict[UUID, PriceFrame],
    tuple[BacktestWarning, ...],
]:
    if not price_frames:
        _raise(BacktestErrorCode.INVALID_PRICE_HISTORY, "Backtest requires at least one asset.")

    prices_by_asset: dict[UUID, dict[date, float]] = {}
    usable_frames: dict[UUID, PriceFrame] = {}
    evaluation_date_sets: list[set[date]] = []
    evaluation_union: set[date] = set()

    for asset_id in sorted(price_frames, key=str):
        frame = price_frames[asset_id]
        if not frame:
            _raise(
                BacktestErrorCode.INVALID_PRICE_HISTORY,
                f"Price frame for asset {asset_id} is empty.",
            )

        usable: list[PriceBar] = []
        price_by_date: dict[date, float] = {}
        previous_date: date | None = None
        for bar in frame:
            if bar.asset_id != asset_id:
                _raise(
                    BacktestErrorCode.INVALID_PRICE_HISTORY,
                    f"Price frame for asset {asset_id} contains another asset identity.",
                )
            if previous_date is not None and bar.trade_date <= previous_date:
                _raise(
                    BacktestErrorCode.INVALID_PRICE_HISTORY,
                    f"Price frame for asset {asset_id} must be strictly ascending and unique.",
                )
            previous_date = bar.trade_date
            if bar.adjusted_close is None:
                continue
            price = _positive_price(
                bar.adjusted_close,
                f"adjusted_close[{asset_id}][{bar.trade_date.isoformat()}]",
            )
            usable.append(bar)
            price_by_date[bar.trade_date] = price

        if not usable:
            _raise(
                BacktestErrorCode.INVALID_PRICE_HISTORY,
                f"Asset {asset_id} has no usable adjusted-close observations.",
            )

        usable_frames[asset_id] = tuple(usable)
        prices_by_asset[asset_id] = price_by_date
        evaluation_dates = {
            trade_date
            for trade_date in price_by_date
            if requested_period_start <= trade_date < requested_period_end_exclusive
        }
        evaluation_date_sets.append(evaluation_dates)
        evaluation_union.update(evaluation_dates)

    common_dates = set(evaluation_date_sets[0])
    common_dates.intersection_update(*evaluation_date_sets[1:])
    aligned_dates = tuple(sorted(common_dates))
    if len(aligned_dates) < 2:
        _raise(
            BacktestErrorCode.INSUFFICIENT_HISTORY,
            "Backtest requires at least two complete-case adjusted-close observations.",
        )

    warnings: tuple[BacktestWarning, ...] = ()
    if len(common_dates) != len(evaluation_union):
        warnings = (
            BacktestWarning(
                code=BacktestWarningCode.INCOMPLETE_DATE_INTERSECTION,
                message=(
                    "Backtest used the complete-case intersection of adjusted-close dates; "
                    "observations missing from any included asset were excluded without "
                    "forward-filling or zero substitution."
                ),
            ),
        )

    return aligned_dates, prices_by_asset, usable_frames, warnings


def _common_history_dates(usable_frames: Mapping[UUID, PriceFrame]) -> tuple[date, ...]:
    date_sets = [{bar.trade_date for bar in frame} for frame in usable_frames.values()]
    common = set(date_sets[0])
    common.intersection_update(*date_sets[1:])
    return tuple(sorted(common))


def _positive_price(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise(
            BacktestErrorCode.INVALID_PRICE_HISTORY,
            f"{field_name} must be a real number.",
        )
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        _raise(
            BacktestErrorCode.INVALID_PRICE_HISTORY,
            f"{field_name} must be finite and positive.",
        )
    return number


def _minimum_history(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _raise(
            BacktestErrorCode.INVALID_INPUT,
            "strategy.minimum_history_observations must be an integer.",
        )
    if value < 0:
        _raise(
            BacktestErrorCode.INVALID_INPUT,
            "strategy.minimum_history_observations must not be negative.",
        )
    return value


def _nonblank(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _raise(BacktestErrorCode.INVALID_INPUT, f"{field_name} must not be blank.")
    return value.strip()


def _raise(code: BacktestErrorCode, message: str) -> NoReturn:
    raise BacktestError(code, message)
