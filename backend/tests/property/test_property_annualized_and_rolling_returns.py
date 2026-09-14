"""Property tests for annualized geometric and rolling cumulative returns."""

import math
from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.config import CALENDAR_DAYS_PER_YEAR
from portfolio_engine.performance.returns import (
    annualized_geometric_return,
    cumulative_return,
    rolling_cumulative_returns,
)

RETURN = st.floats(
    min_value=-0.90,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
)

ROLLING_CASE = st.lists(RETURN, min_size=1, max_size=30).flatmap(
    lambda values: st.tuples(
        st.just(tuple(values)),
        st.integers(min_value=1, max_value=len(values)),
    )
)

PREFIX_FUTURE_CASE = st.lists(RETURN, min_size=1, max_size=20).flatmap(
    lambda prefix: st.tuples(
        st.just(tuple(prefix)),
        st.lists(RETURN, min_size=0, max_size=10).map(tuple),
        st.integers(min_value=1, max_value=len(prefix)),
    )
)


@given(
    wealth_ratio=st.floats(
        min_value=0.5,
        max_value=2.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    elapsed_days=st.integers(min_value=30, max_value=3650),
)
def test_annualization_round_trips_to_original_wealth_ratio(
    wealth_ratio: float,
    elapsed_days: int,
) -> None:
    period_start = date(2000, 1, 1)
    period_end = period_start + timedelta(days=elapsed_days)

    result = annualized_geometric_return(
        wealth_ratio,
        period_start=period_start,
        period_end=period_end,
    )
    reconstructed = math.exp(math.log1p(result.value) * result.elapsed_years)

    assert reconstructed == pytest.approx(
        wealth_ratio,
        rel=1e-12,
        abs=1e-12,
    )
    assert result.is_short_period is (elapsed_days < CALENDAR_DAYS_PER_YEAR)


@given(case=ROLLING_CASE)
def test_each_rolling_result_matches_its_trailing_window(
    case: tuple[tuple[float, ...], int],
) -> None:
    returns, window_size = case
    result = rolling_cumulative_returns(returns, window_size)
    expected = tuple(
        cumulative_return(returns[start : start + window_size])
        for start in range(len(returns) - window_size + 1)
    )

    assert result == pytest.approx(expected)


@given(case=PREFIX_FUTURE_CASE)
def test_rolling_returns_are_independent_of_future_observations(
    case: tuple[tuple[float, ...], tuple[float, ...], int],
) -> None:
    prefix, future, window_size = case
    prefix_result = rolling_cumulative_returns(prefix, window_size)
    extended_result = rolling_cumulative_returns(prefix + future, window_size)

    assert extended_result[: len(prefix_result)] == pytest.approx(prefix_result)
