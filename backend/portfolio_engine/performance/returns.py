"""Canonical return calculations for the quantitative engine.

Development guide references: Sections 11.1, 11.2, 11.3, 11.4, and 11.14.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from numbers import Real

from portfolio_engine.config import CALENDAR_DAYS_PER_YEAR

type ReturnSeries = tuple[float, ...]


@dataclass(frozen=True, slots=True)
class AnnualizedReturnResult:
    """Typed annualized geometric-return result with period metadata."""

    value: float
    wealth_ratio: float
    elapsed_days: int
    elapsed_years: float
    is_short_period: bool


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


def annualized_geometric_return(
    wealth_ratio: float,
    *,
    period_start: date,
    period_end: date,
) -> AnnualizedReturnResult:
    """Annualize a positive wealth ratio using elapsed calendar days.

    The canonical annualization is ``wealth_ratio ** (365.2425 / days) - 1``.
    The result remains explicitly marked as annualized when the analyzed period
    is shorter than one calendar year.
    """
    normalized_wealth_ratio = _finite_real(
        wealth_ratio,
        field_name="wealth_ratio",
    )

    if normalized_wealth_ratio <= 0.0:
        raise ValueError("wealth_ratio must be positive")

    elapsed_days = (period_end - period_start).days

    if elapsed_days <= 0:
        raise ValueError("period_end must be later than period_start")

    elapsed_years = elapsed_days / CALENDAR_DAYS_PER_YEAR
    annualized_log_growth = math.log(normalized_wealth_ratio) / elapsed_years

    try:
        value = math.expm1(annualized_log_growth)
    except OverflowError as exc:
        raise ValueError("annualized geometric return must be finite") from exc

    if not math.isfinite(value):
        raise ValueError("annualized geometric return must be finite")

    return AnnualizedReturnResult(
        value=value,
        wealth_ratio=normalized_wealth_ratio,
        elapsed_days=elapsed_days,
        elapsed_years=elapsed_years,
        is_short_period=elapsed_days < CALENDAR_DAYS_PER_YEAR,
    )


def cagr(
    beginning_value: float,
    ending_value: float,
    *,
    period_start: date,
    period_end: date,
) -> AnnualizedReturnResult:
    """Return CAGR from beginning and ending values over calendar dates."""
    normalized_beginning = _finite_real(
        beginning_value,
        field_name="beginning_value",
    )
    normalized_ending = _finite_real(
        ending_value,
        field_name="ending_value",
    )

    if normalized_beginning == 0.0:
        raise ValueError("beginning_value must not be zero")

    return annualized_geometric_return(
        normalized_ending / normalized_beginning,
        period_start=period_start,
        period_end=period_end,
    )


def rolling_cumulative_returns(
    returns: Sequence[float],
    window_size: int,
) -> ReturnSeries:
    """Return trailing N-period cumulative returns without future observations.

    The value ending at each available position uses exactly the preceding
    ``window_size`` return observations, including the observation at that
    endpoint. If fewer than ``window_size`` observations exist, no rolling
    result is available.
    """
    if isinstance(window_size, bool) or not isinstance(window_size, int):
        raise TypeError("window_size must be an integer")

    if window_size <= 0:
        raise ValueError("window_size must be positive")

    normalized_returns = _validated_returns(returns)

    if len(normalized_returns) < window_size:
        return ()

    return tuple(
        cumulative_return(normalized_returns[start : start + window_size])
        for start in range(len(normalized_returns) - window_size + 1)
    )


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
