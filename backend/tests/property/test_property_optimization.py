"""Property tests for long-only optimization invariants."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from portfolio_engine.optimization import build_problem, minimum_variance_portfolio


@settings(max_examples=40, deadline=None)
@given(
    variance_a=st.floats(min_value=0.001, max_value=0.50, allow_nan=False, allow_infinity=False),
    variance_b=st.floats(min_value=0.001, max_value=0.50, allow_nan=False, allow_infinity=False),
    expected_a=st.floats(min_value=-0.50, max_value=0.50, allow_nan=False, allow_infinity=False),
    expected_b=st.floats(min_value=-0.50, max_value=0.50, allow_nan=False, allow_infinity=False),
)
def test_minimum_variance_long_only_weights_remain_feasible(
    variance_a: float,
    variance_b: float,
    expected_a: float,
    expected_b: float,
) -> None:
    problem = build_problem(
        asset_keys=("A", "B"),
        expected_returns=(expected_a, expected_b),
        covariance=((variance_a, 0.0), (0.0, variance_b)),
    )

    result = minimum_variance_portfolio(problem)

    assert sum(result.weights) == pytest.approx(1.0, abs=1e-8)
    assert all(-1e-8 <= weight <= 1.0 + 1e-8 for weight in result.weights)
