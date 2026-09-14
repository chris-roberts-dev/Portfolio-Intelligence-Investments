"""Property tests for canonical return calculations."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.performance.returns import (
    cumulative_return,
    log_returns,
    simple_returns,
)

POSITIVE_PRICE = st.floats(
    min_value=0.01,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)


@given(
    prices=st.lists(POSITIVE_PRICE, min_size=2, max_size=30).map(tuple),
    scale=st.floats(
        min_value=0.01,
        max_value=100.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_returns_are_invariant_to_positive_price_scaling(
    prices: tuple[float, ...],
    scale: float,
) -> None:
    scaled_prices = tuple(price * scale for price in prices)

    assert simple_returns(scaled_prices) == pytest.approx(
        simple_returns(prices),
        rel=1e-12,
        abs=1e-12,
    )
    assert log_returns(scaled_prices) == pytest.approx(
        log_returns(prices),
        rel=1e-12,
        abs=1e-12,
    )


@given(prices=st.lists(POSITIVE_PRICE, min_size=2, max_size=30).map(tuple))
def test_compounded_simple_returns_equal_endpoint_price_ratio(
    prices: tuple[float, ...],
) -> None:
    compounded_wealth_ratio = 1.0 + cumulative_return(simple_returns(prices))
    endpoint_wealth_ratio = prices[-1] / prices[0]

    assert math.isclose(
        compounded_wealth_ratio,
        endpoint_wealth_ratio,
        rel_tol=1e-8,
        abs_tol=1e-12,
    )


@given(prices=st.lists(POSITIVE_PRICE, min_size=2, max_size=30).map(tuple))
def test_log_returns_telescope_to_endpoint_log_ratio(
    prices: tuple[float, ...],
) -> None:
    result = sum(log_returns(prices))
    expected = math.log(prices[-1]) - math.log(prices[0])

    assert math.isclose(result, expected, rel_tol=1e-10, abs_tol=1e-12)
