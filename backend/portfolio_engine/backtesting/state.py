"""Long-only deterministic portfolio state helpers for Phase 6 backtesting.

Development guide references: Sections 10.2, 14.6, and 19.4.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date
from typing import NoReturn
from uuid import UUID

from portfolio_engine.backtesting.contracts import (
    BacktestError,
    BacktestErrorCode,
    BacktestInitialPosition,
    PortfolioLedgerState,
    PortfolioPositionSnapshot,
    PortfolioState,
    PositionQuantity,
)
from portfolio_engine.config import WEIGHT_SUM_TOLERANCE


def build_initial_ledger_state(
    *,
    positions: Sequence[BacktestInitialPosition],
    cash: float,
    asset_universe: frozenset[UUID],
) -> PortfolioLedgerState:
    """Validate and normalize the initial long-only quantity/cash state."""
    normalized_cash = _finite_nonnegative(cash, "initial_cash")
    seen: set[UUID] = set()
    normalized_positions: list[PositionQuantity] = []

    for index, position in enumerate(positions):
        if position.asset_id not in asset_universe:
            _raise(
                BacktestErrorCode.INVALID_INPUT,
                f"initial_positions[{index}] references an asset outside the backtest universe.",
            )
        if position.asset_id in seen:
            _raise(
                BacktestErrorCode.INVALID_INPUT,
                f"Duplicate initial position asset at index {index}.",
            )
        seen.add(position.asset_id)
        quantity = _finite_nonnegative(
            position.quantity,
            f"initial_positions[{index}].quantity",
        )
        if quantity <= WEIGHT_SUM_TOLERANCE:
            continue
        normalized_positions.append(PositionQuantity(asset_id=position.asset_id, quantity=quantity))

    return PortfolioLedgerState(
        positions=tuple(sorted(normalized_positions, key=lambda item: str(item.asset_id))),
        cash=normalized_cash,
    )


def value_portfolio_state(
    *,
    as_of: date,
    ledger: PortfolioLedgerState,
    prices: Mapping[UUID, float],
) -> PortfolioState:
    """Value immutable quantity/cash state at one complete-case price observation."""
    position_values: list[tuple[PositionQuantity, float]] = []
    for position in ledger.positions:
        price = prices.get(position.asset_id)
        if price is None:
            _raise(
                BacktestErrorCode.INVALID_PRICE_HISTORY,
                f"No adjusted-close price is available for held asset {position.asset_id}.",
            )
        market_value = position.quantity * price
        position_values.append((position, market_value))

    total_value = ledger.cash + math.fsum(value for _, value in position_values)
    if total_value <= 0.0:
        _raise(
            BacktestErrorCode.NONPOSITIVE_PORTFOLIO_VALUE,
            "Backtest portfolio value must remain positive.",
        )

    positions = tuple(
        PortfolioPositionSnapshot(
            asset_id=position.asset_id,
            quantity=position.quantity,
            market_value=market_value,
            weight=market_value / total_value,
        )
        for position, market_value in position_values
    )
    return PortfolioState(
        as_of=as_of,
        positions=positions,
        cash=ledger.cash,
        cash_weight=ledger.cash / total_value,
        total_value=total_value,
    )


def quantities_by_asset(ledger: PortfolioLedgerState) -> dict[UUID, float]:
    """Return a mutable quantity map for deterministic execution internals."""
    return {position.asset_id: position.quantity for position in ledger.positions}


def ledger_from_quantities(
    *,
    quantities: Mapping[UUID, float],
    cash: float,
) -> PortfolioLedgerState:
    """Create normalized immutable state after execution."""
    normalized_cash = cash
    if normalized_cash < -WEIGHT_SUM_TOLERANCE:
        _raise(
            BacktestErrorCode.NEGATIVE_CASH,
            "Backtest execution created negative cash.",
        )
    if normalized_cash < 0.0:
        normalized_cash = 0.0

    positions: list[PositionQuantity] = []
    for asset_id, quantity in sorted(quantities.items(), key=lambda item: str(item[0])):
        if quantity < -WEIGHT_SUM_TOLERANCE:
            _raise(
                BacktestErrorCode.INSUFFICIENT_POSITION,
                f"Backtest execution created a short position in asset {asset_id}.",
            )
        if quantity <= WEIGHT_SUM_TOLERANCE:
            continue
        positions.append(PositionQuantity(asset_id=asset_id, quantity=max(0.0, quantity)))

    return PortfolioLedgerState(positions=tuple(positions), cash=normalized_cash)


def finite_unit_rate(value: object, field_name: str) -> float:
    """Validate a commission/slippage rate in the canonical unit interval."""
    number = finite_number(value, field_name)
    if number < 0.0 or number > 1.0:
        _raise(
            BacktestErrorCode.INVALID_INPUT,
            f"{field_name} must be between zero and one.",
        )
    return number


def finite_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise(BacktestErrorCode.INVALID_INPUT, f"{field_name} must be a real number.")
    number = float(value)
    if not math.isfinite(number):
        _raise(BacktestErrorCode.INVALID_INPUT, f"{field_name} must be finite.")
    return number


def _finite_nonnegative(value: object, field_name: str) -> float:
    number = finite_number(value, field_name)
    if number < 0.0:
        _raise(BacktestErrorCode.INVALID_INPUT, f"{field_name} must not be negative.")
    return number


def _raise(code: BacktestErrorCode, message: str) -> NoReturn:
    raise BacktestError(code, message)
