from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.backtesting import (
    BacktestDataProvenance,
    BacktestInitialPosition,
    OrderIntent,
    OrderSide,
    StrategyContext,
    run_backtest,
)
from portfolio_engine.contracts.market_data import PriceBar

A = UUID("00000000-0000-0000-0000-000000000001")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
RETRIEVED_AT = datetime(2026, 1, 6, 22, 0, tzinfo=UTC)
PROVENANCE = BacktestDataProvenance(provider="mock", retrieved_at=RETRIEVED_AT)


@dataclass
class OversizedBuyStrategy:
    name: str = "oversized-buy"
    version: str = "1.0"
    minimum_history_observations: int = 1

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        if context.as_of == D1:
            return (OrderIntent(asset_id=A, side=OrderSide.BUY, quantity=1000.0),)
        return ()


@dataclass
class NoOpStrategy:
    name: str = "noop"
    version: str = "1.0"
    minimum_history_observations: int = 1

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        return ()


@dataclass
class SellOnceStrategy:
    quantity: float
    name: str = "sell-once"
    version: str = "1.0"
    minimum_history_observations: int = 1

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        if context.as_of == D1:
            return (
                OrderIntent(
                    asset_id=A,
                    side=OrderSide.SELL,
                    quantity=self.quantity,
                ),
            )
        return ()


def _frame(price: float) -> tuple[PriceBar, ...]:
    return tuple(
        PriceBar(
            asset_id=A,
            trade_date=trade_date,
            open=price,
            high=price,
            low=price,
            close=price,
            adjusted_close=price,
            volume=100,
            source="mock",
            retrieved_at=RETRIEVED_AT,
        )
        for trade_date in (D1, D2)
    )


@given(
    commission_rate=st.floats(
        min_value=0.0,
        max_value=0.05,
        allow_nan=False,
        allow_infinity=False,
    ),
    slippage_rate=st.floats(
        min_value=0.0,
        max_value=0.05,
        allow_nan=False,
        allow_infinity=False,
    ),
    price=st.floats(
        min_value=1.0,
        max_value=500.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_backtest_preserves_nonnegative_cash_long_only_state_and_weight_identity(
    commission_rate: float,
    slippage_rate: float,
    price: float,
) -> None:
    result = run_backtest(
        price_frames={A: _frame(price)},
        initial_positions=(),
        initial_cash=100.0,
        strategy=OversizedBuyStrategy(),
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )

    for snapshot in result.snapshots:
        assert snapshot.cash >= -1e-9
        assert all(position.quantity >= -1e-9 for position in snapshot.positions)
        assert all(position.weight >= -1e-9 for position in snapshot.positions)
        total_weight = snapshot.cash_weight + sum(
            position.weight for position in snapshot.positions
        )
        assert total_weight == pytest.approx(1.0, abs=1e-9)


@given(
    price=st.floats(
        min_value=1.0,
        max_value=500.0,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_identical_backtest_inputs_replay_deterministically(price: float) -> None:
    kwargs = {
        "price_frames": {A: _frame(price)},
        "initial_positions": (),
        "initial_cash": 100.0,
        "strategy": NoOpStrategy(),
        "requested_period_start": D1,
        "requested_period_end_exclusive": D3,
        "data_provenance": PROVENANCE,
    }
    first = run_backtest(**kwargs)
    second = run_backtest(**kwargs)
    assert first == second
    assert first.trade_count == 0
    assert first.total_cost == pytest.approx(0.0)


@given(
    sell_quantity=st.floats(
        min_value=0.001,
        max_value=10.0,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_valid_sell_orders_never_create_short_positions(sell_quantity: float) -> None:
    result = run_backtest(
        price_frames={A: _frame(10.0)},
        initial_positions=(BacktestInitialPosition(asset_id=A, quantity=10.0),),
        initial_cash=0.0,
        strategy=SellOnceStrategy(quantity=sell_quantity),
        requested_period_start=D1,
        requested_period_end_exclusive=D3,
        data_provenance=PROVENANCE,
    )

    assert all(
        position.quantity >= -1e-9
        for snapshot in result.snapshots
        for position in snapshot.positions
    )
