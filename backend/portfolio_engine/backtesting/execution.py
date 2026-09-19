"""Order validation and deterministic simulated fills for Phase 6 backtesting.

Development guide references: Sections 14.3, 14.5-14.6, and 19.4.
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
    BacktestExecutionEvent,
    BacktestWarning,
    BacktestWarningCode,
    OrderIntent,
    OrderSide,
    PortfolioLedgerState,
    SimulatedFill,
)
from portfolio_engine.backtesting.state import (
    finite_number,
    ledger_from_quantities,
    quantities_by_asset,
    value_portfolio_state,
)
from portfolio_engine.config import WEIGHT_SUM_TOLERANCE


def normalize_orders(
    orders: Sequence[OrderIntent],
    *,
    asset_universe: frozenset[UUID],
) -> tuple[OrderIntent, ...]:
    """Validate strategy order intents without interpreting strategy meaning."""
    seen: set[UUID] = set()
    normalized: list[OrderIntent] = []
    for index, order in enumerate(orders):
        if order.asset_id not in asset_universe:
            _raise(
                BacktestErrorCode.INVALID_ORDER,
                f"orders[{index}] references an asset outside the backtest universe.",
            )
        if order.asset_id in seen:
            _raise(
                BacktestErrorCode.INVALID_ORDER,
                f"orders[{index}] duplicates an asset in the same decision.",
            )
        if not isinstance(order.side, OrderSide):
            _raise(
                BacktestErrorCode.INVALID_ORDER,
                f"orders[{index}].side must be BUY or SELL.",
            )
        seen.add(order.asset_id)
        quantity = finite_number(order.quantity, f"orders[{index}].quantity")
        if quantity <= 0.0:
            _raise(
                BacktestErrorCode.INVALID_ORDER,
                f"orders[{index}].quantity must be positive.",
            )
        normalized.append(OrderIntent(asset_id=order.asset_id, side=order.side, quantity=quantity))
    return tuple(sorted(normalized, key=lambda item: str(item.asset_id)))


def execute_orders(
    *,
    ledger: PortfolioLedgerState,
    orders: tuple[OrderIntent, ...],
    prices: Mapping[UUID, float],
    decision_date: date,
    execution_date: date,
    commission_rate: float,
    slippage_rate: float,
) -> tuple[PortfolioLedgerState, BacktestExecutionEvent, tuple[BacktestWarning, ...]]:
    """Execute one normalized order batch at the next aligned adjusted close."""
    if execution_date <= decision_date:
        _raise(
            BacktestErrorCode.INVALID_ORDER,
            "Backtest execution date must be later than its decision date.",
        )

    pre_trade = value_portfolio_state(as_of=execution_date, ledger=ledger, prices=prices)
    quantities = quantities_by_asset(ledger)
    cash = ledger.cash
    fills: list[SimulatedFill] = []

    sell_orders = tuple(order for order in orders if order.side is OrderSide.SELL)
    buy_orders = tuple(order for order in orders if order.side is OrderSide.BUY)

    for order in sell_orders:
        held_quantity = quantities.get(order.asset_id, 0.0)
        if order.quantity > held_quantity + WEIGHT_SUM_TOLERANCE:
            _raise(
                BacktestErrorCode.INSUFFICIENT_POSITION,
                (
                    f"Sell order for asset {order.asset_id} requests {order.quantity} shares "
                    f"but only {held_quantity} are held."
                ),
            )
        fill = _fill(
            order=order,
            quantity=min(order.quantity, held_quantity),
            reference_price=prices[order.asset_id],
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        quantities[order.asset_id] = max(0.0, held_quantity - fill.quantity)
        cash += fill.fill_notional - fill.commission_cost
        fills.append(fill)

    requested_buy_cost = math.fsum(
        buy_cash_cost(
            quantity=order.quantity,
            reference_price=prices[order.asset_id],
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        for order in buy_orders
    )
    buy_scale = 1.0
    warnings: list[BacktestWarning] = []
    if requested_buy_cost > cash and requested_buy_cost > 0.0:
        buy_scale = max(0.0, cash / requested_buy_cost)
        warnings.append(
            BacktestWarning(
                code=BacktestWarningCode.BUY_SCALED_TO_AVAILABLE_CASH,
                message=(
                    "One or more buy orders were proportionally scaled to preserve "
                    "non-negative cash after commission and slippage."
                ),
            )
        )

    for order in buy_orders:
        quantity = order.quantity * buy_scale
        if quantity <= WEIGHT_SUM_TOLERANCE:
            continue
        fill = _fill(
            order=order,
            quantity=quantity,
            reference_price=prices[order.asset_id],
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
        )
        cash_cost = fill.fill_notional + fill.commission_cost
        if cash_cost > cash and cash_cost - cash <= WEIGHT_SUM_TOLERANCE:
            cash_cost = cash
        if cash_cost > cash + WEIGHT_SUM_TOLERANCE:
            _raise(
                BacktestErrorCode.NEGATIVE_CASH,
                "Scaled backtest buy would create negative cash.",
            )
        cash -= cash_cost
        quantities[order.asset_id] = quantities.get(order.asset_id, 0.0) + fill.quantity
        fills.append(fill)

    next_ledger = ledger_from_quantities(quantities=quantities, cash=cash)
    post_trade = value_portfolio_state(
        as_of=execution_date,
        ledger=next_ledger,
        prices=prices,
    )
    commission = math.fsum(fill.commission_cost for fill in fills)
    slippage = math.fsum(fill.slippage_cost for fill in fills)
    gross_fill_notional = math.fsum(fill.fill_notional for fill in fills)
    turnover = gross_fill_notional / pre_trade.total_value

    event = BacktestExecutionEvent(
        decision_date=decision_date,
        execution_date=execution_date,
        orders=orders,
        fills=tuple(fills),
        pre_trade_value=pre_trade.total_value,
        post_trade_value=post_trade.total_value,
        turnover=turnover,
        commission_cost=commission,
        slippage_cost=slippage,
        total_cost=commission + slippage,
        buy_scale=buy_scale,
    )
    return next_ledger, event, tuple(warnings)


def _fill(
    *,
    order: OrderIntent,
    quantity: float,
    reference_price: float,
    commission_rate: float,
    slippage_rate: float,
) -> SimulatedFill:
    if order.side is OrderSide.BUY:
        fill_price = buy_fill_price(reference_price, slippage_rate)
    else:
        fill_price = sell_fill_price(reference_price, slippage_rate)

    fill_notional = quantity * fill_price
    commission = commission_cost(fill_notional, commission_rate)
    return SimulatedFill(
        asset_id=order.asset_id,
        side=order.side,
        quantity=quantity,
        reference_price=reference_price,
        fill_price=fill_price,
        fill_notional=fill_notional,
        commission_cost=commission,
        slippage_cost=slippage_cost(
            quantity=quantity,
            reference_price=reference_price,
            fill_price=fill_price,
        ),
    )


def buy_fill_price(reference_price: float, slippage_rate: float) -> float:
    """Return the canonical Section 14.5 slipped buy fill price."""
    return reference_price * (1.0 + slippage_rate)


def sell_fill_price(reference_price: float, slippage_rate: float) -> float:
    """Return the canonical Section 14.5 slipped sell fill price."""
    return reference_price * (1.0 - slippage_rate)


def commission_cost(fill_notional: float, commission_rate: float) -> float:
    """Return commission from absolute executed fill notional."""
    return abs(fill_notional) * commission_rate


def slippage_cost(
    *,
    quantity: float,
    reference_price: float,
    fill_price: float,
) -> float:
    """Return the absolute reference-to-fill slippage cost."""
    return quantity * abs(fill_price - reference_price)


def buy_cash_cost(
    *,
    quantity: float,
    reference_price: float,
    commission_rate: float,
    slippage_rate: float,
) -> float:
    """Return cash required for a buy including slippage and commission."""
    fill_price = buy_fill_price(reference_price, slippage_rate)
    fill_notional = quantity * fill_price
    return fill_notional + commission_cost(fill_notional, commission_rate)


def _raise(code: BacktestErrorCode, message: str) -> NoReturn:
    raise BacktestError(code, message)
