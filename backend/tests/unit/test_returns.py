"""Unit tests for canonical return calculations."""

import math

import pytest

from portfolio_engine.performance.returns import (
    cumulative_return,
    log_returns,
    simple_returns,
)


def test_constant_prices_produce_zero_simple_and_log_returns() -> None:
    prices = (100.0, 100.0, 100.0, 100.0)

    assert simple_returns(prices) == (0.0, 0.0, 0.0)
    assert log_returns(prices) == (0.0, 0.0, 0.0)


def test_price_doubling_produces_one_hundred_percent_simple_return() -> None:
    returns = simple_returns((100.0, 200.0))

    assert returns == (1.0,)
    assert cumulative_return(returns) == 1.0


def test_known_multi_period_compounding_fixture() -> None:
    returns = (0.10, -0.10, 0.05)

    assert cumulative_return(returns) == pytest.approx(0.0395)


def test_log_return_matches_canonical_definition() -> None:
    result = log_returns((100.0, 110.0))

    assert result == pytest.approx((math.log(1.1),))


def test_single_price_has_no_return_observation() -> None:
    assert simple_returns((100.0,)) == ()
    assert log_returns((100.0,)) == ()


def test_empty_return_series_has_zero_cumulative_return() -> None:
    assert cumulative_return(()) == 0.0


@pytest.mark.parametrize(
    "prices",
    [
        (100.0, 0.0),
        (100.0, -1.0),
        (100.0, float("nan")),
        (100.0, float("inf")),
    ],
)
def test_price_return_functions_reject_invalid_prices(
    prices: tuple[float, float],
) -> None:
    with pytest.raises(ValueError):
        simple_returns(prices)

    with pytest.raises(ValueError):
        log_returns(prices)


@pytest.mark.parametrize(
    "returns",
    [
        (0.01, float("nan")),
        (0.01, float("inf")),
        (0.01, float("-inf")),
    ],
)
def test_cumulative_return_rejects_nonfinite_returns(
    returns: tuple[float, float],
) -> None:
    with pytest.raises(ValueError):
        cumulative_return(returns)
