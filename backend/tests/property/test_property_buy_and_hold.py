from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.backtesting import BacktestDataProvenance, run_backtest
from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.strategies import BuyAndHoldStrategy, BuyAndHoldTargetWeight

A = UUID("00000000-0000-0000-0000-000000000001")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
D4 = date(2026, 1, 7)
RETRIEVED_AT = datetime(2026, 1, 6, 22, 0, tzinfo=UTC)
PROVENANCE = BacktestDataProvenance(provider="mock", retrieved_at=RETRIEVED_AT)


def _frame(
    decision_price: float,
    execution_price: float,
    ending_price: float,
) -> tuple[PriceBar, ...]:
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
        for trade_date, price in (
            (D1, decision_price),
            (D2, execution_price),
            (D3, ending_price),
        )
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
    decision_price=st.floats(
        min_value=1.0,
        max_value=500.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    execution_price=st.floats(
        min_value=1.0,
        max_value=500.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_buy_and_hold_remains_long_only_and_nonnegative_cash(
    commission_rate: float,
    slippage_rate: float,
    decision_price: float,
    execution_price: float,
) -> None:
    result = run_backtest(
        price_frames={A: _frame(decision_price, execution_price, execution_price)},
        initial_positions=(),
        initial_cash=100.0,
        strategy=BuyAndHoldStrategy(targets=(BuyAndHoldTargetWeight(A, 1.0),)),
        requested_period_start=D1,
        requested_period_end_exclusive=D4,
        data_provenance=PROVENANCE,
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )

    assert len(result.decisions) == 1
    assert len(result.executions) == 1
    for snapshot in result.snapshots:
        assert snapshot.cash >= -1e-9
        assert all(position.quantity >= -1e-9 for position in snapshot.positions)
        assert snapshot.cash_weight + sum(
            position.weight for position in snapshot.positions
        ) == pytest.approx(1.0, abs=1e-9)


@given(
    low_cost=st.floats(
        min_value=0.0,
        max_value=0.02,
        allow_nan=False,
        allow_infinity=False,
    ),
    extra_cost=st.floats(
        min_value=0.0,
        max_value=0.02,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_increasing_commission_cannot_improve_buy_and_hold_ending_value(
    low_cost: float,
    extra_cost: float,
) -> None:
    high_cost = min(1.0, low_cost + extra_cost)
    kwargs = {
        "price_frames": {A: _frame(10.0, 10.0, 12.0)},
        "initial_positions": (),
        "initial_cash": 100.0,
        "strategy": BuyAndHoldStrategy(targets=(BuyAndHoldTargetWeight(A, 1.0),)),
        "requested_period_start": D1,
        "requested_period_end_exclusive": D4,
        "data_provenance": PROVENANCE,
        "slippage_rate": 0.0,
    }
    lower = run_backtest(commission_rate=low_cost, **kwargs)
    higher = run_backtest(commission_rate=high_cost, **kwargs)

    assert higher.ending_value <= lower.ending_value + 1e-9
