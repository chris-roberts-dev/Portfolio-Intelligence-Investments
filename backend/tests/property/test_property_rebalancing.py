from __future__ import annotations

from uuid import UUID

from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.rebalancing import CurrentValue, TargetWeight, simulate_rebalance

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")


@given(
    current_a=st.floats(min_value=0.0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    current_b=st.floats(min_value=0.0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    target_a=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)
def test_trade_notionals_net_to_zero_for_fully_invested_target(
    current_a: float,
    current_b: float,
    target_a: float,
) -> None:
    if current_a + current_b <= 1e-9:
        return
    result = simulate_rebalance(
        (CurrentValue(A, current_a), CurrentValue(B, current_b)),
        (TargetWeight(A, target_a), TargetWeight(B, 1.0 - target_a)),
    )
    assert abs(sum(line.trade_notional for line in result.lines)) <= 1e-6
