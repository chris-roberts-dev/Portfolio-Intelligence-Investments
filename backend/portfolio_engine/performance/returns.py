"""Canonical return calculations for the quantitative engine.

Development guide references: Sections 11.1, 11.2, and 11.3.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from numbers import Real

type ReturnSeries = tuple[float, ...]


def simple_returns(prices: Sequence[float]) -> ReturnSeries:
    """Return canonical period-over-period simple returns for positive prices.

    For prices ``P_t``, each result is ``P_t / P_(t-1) - 1``. A price series
    with fewer than two observations has no return observations and therefore
    returns an empty tuple.
    """
    normalized_prices = _validated_prices(prices)
    returns: list[float] = []

    for previous_price, current_price in zip(
        normalized_prices,
        normalized_prices[1:],
        strict=False,
    ):
        period_return = current_price / previous_price - 1.0

        if not math.isfinite(period_return):
            raise ValueError("simple return must be finite")

        returns.append(period_return)

    return tuple(returns)


def log_returns(prices: Sequence[float]) -> ReturnSeries:
    """Return canonical period-over-period log returns for positive prices.

    Log returns are calculated as ``ln(P_t) - ln(P_(t-1))``. This is
    algebraically equivalent to ``ln(P_t / P_(t-1))`` while avoiding an
    avoidable intermediate overflow for extreme positive finite prices.
    """
    normalized_prices = _validated_prices(prices)

    return tuple(
        math.log(current_price) - math.log(previous_price)
        for previous_price, current_price in zip(
            normalized_prices,
            normalized_prices[1:],
            strict=False,
        )
    )


def cumulative_return(returns: Sequence[float]) -> float:
    """Return canonical compounded cumulative simple return.

    The canonical definition is ``product(1 + r_t) - 1``. An empty return
    series represents no elapsed return observations and therefore has a
    cumulative return of zero.
    """
    normalized_returns = _validated_returns(returns)
    wealth_ratio = 1.0

    for period_return in normalized_returns:
        wealth_ratio *= 1.0 + period_return

        if not math.isfinite(wealth_ratio):
            raise ValueError("cumulative wealth ratio must remain finite")

    result = wealth_ratio - 1.0

    if not math.isfinite(result):
        raise ValueError("cumulative return must be finite")

    return result


def _validated_prices(prices: Sequence[float]) -> tuple[float, ...]:
    normalized: list[float] = []

    for index, value in enumerate(prices):
        number = _finite_real(value, field_name=f"prices[{index}]")

        if number <= 0.0:
            raise ValueError(f"prices[{index}] must be positive")

        normalized.append(number)

    return tuple(normalized)


def _validated_returns(returns: Sequence[float]) -> ReturnSeries:
    return tuple(
        _finite_real(value, field_name=f"returns[{index}]") for index, value in enumerate(returns)
    )


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
