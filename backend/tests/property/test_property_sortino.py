"""Property tests for downside deviation and Sortino ratio."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from portfolio_engine.performance.downside import (
    downside_deviation,
    sortino_ratio,
)

RETURN_SERIES = st.lists(
    st.integers(min_value=-1000, max_value=1000),
    min_size=2,
    max_size=30,
).map(tuple)


@given(
    values=RETURN_SERIES,
    scale=st.integers(min_value=1, max_value=10),
)
def test_downside_deviation_scales_by_positive_factor(
    values: tuple[int, ...],
    scale: int,
) -> None:
    excess_returns = tuple(value / 10_000.0 for value in values)
    scaled = tuple(value * scale for value in excess_returns)

    assert downside_deviation(scaled) == pytest.approx(
        scale * downside_deviation(excess_returns),
        rel=1e-12,
        abs=1e-12,
    )


@given(values=RETURN_SERIES)
def test_downside_deviation_is_nonnegative(values: tuple[int, ...]) -> None:
    excess_returns = tuple(value / 10_000.0 for value in values)

    assert downside_deviation(excess_returns) >= 0.0


@given(
    values=RETURN_SERIES,
    scale=st.integers(min_value=1, max_value=10),
)
def test_zero_mar_sortino_is_invariant_to_positive_scaling(
    values: tuple[int, ...],
    scale: int,
) -> None:
    returns = tuple(value / 10_000.0 for value in values)
    assume(downside_deviation(returns) > 0.0)

    scaled_returns = tuple(value * scale for value in returns)
    base = sortino_ratio(
        returns,
        minimum_acceptable_return_annual=0.0,
    )
    scaled = sortino_ratio(
        scaled_returns,
        minimum_acceptable_return_annual=0.0,
    )

    assert base.value is not None
    assert scaled.value == pytest.approx(
        base.value,
        rel=1e-11,
        abs=1e-12,
    )


@given(
    prefix=RETURN_SERIES,
    future=st.lists(
        st.integers(min_value=-1000, max_value=1000),
        max_size=20,
    ).map(tuple),
)
def test_prefix_sortino_does_not_depend_on_future_observations(
    prefix: tuple[int, ...],
    future: tuple[int, ...],
) -> None:
    prefix_returns = tuple(value / 10_000.0 for value in prefix)
    extended_returns = prefix_returns + tuple(value / 10_000.0 for value in future)
    same_prefix = extended_returns[: len(prefix_returns)]

    assert sortino_ratio(
        same_prefix,
        minimum_acceptable_return_annual=0.0,
    ) == sortino_ratio(
        prefix_returns,
        minimum_acceptable_return_annual=0.0,
    )
