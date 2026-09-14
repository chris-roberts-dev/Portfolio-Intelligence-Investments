"""Independent analytical fixtures for canonical return calculations."""

import math

import pytest

from portfolio_engine.performance.returns import (
    cumulative_return,
    log_returns,
    simple_returns,
)


def test_known_price_path_matches_independently_derived_returns() -> None:
    prices = (100.0, 110.0, 99.0, 103.95)

    assert simple_returns(prices) == pytest.approx((0.10, -0.10, 0.05))
    assert cumulative_return(simple_returns(prices)) == pytest.approx(0.0395)
    assert log_returns(prices) == pytest.approx(
        (
            math.log(1.10),
            math.log(0.90),
            math.log(1.05),
        )
    )
