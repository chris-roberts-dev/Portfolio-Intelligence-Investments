from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.rebalancing import (
    HistoricalRebalancePolicy,
    RebalanceSchedule,
    TargetWeight,
    compare_historical_rebalancing,
)

A = UUID("00000000-0000-0000-0000-000000000001")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
RETRIEVED_AT = datetime(2026, 1, 5, 22, 0, tzinfo=UTC)


def _frame() -> tuple[PriceBar, ...]:
    return tuple(
        PriceBar(
            asset_id=A,
            trade_date=trade_date,
            open=10.0,
            high=10.0,
            low=10.0,
            close=10.0,
            adjusted_close=10.0,
            volume=100,
            source="mock",
            retrieved_at=RETRIEVED_AT,
        )
        for trade_date in (D1, D2)
    )


@given(
    commission_rate=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
    slippage_rate=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
)
def test_historical_execution_never_creates_negative_cash(
    commission_rate: float,
    slippage_rate: float,
) -> None:
    result = compare_historical_rebalancing(
        price_frames={A: _frame()},
        initial_positions=(),
        initial_cash=100.0,
        targets=(TargetWeight(A, 1.0),),
        policies=(HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),),
        commission_rate=commission_rate,
        slippage_rate=slippage_rate,
    )
    assert all(snapshot.cash_value >= -1e-9 for snapshot in result.policy_results[0].snapshots)
