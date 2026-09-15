"""Canonical daily time-weighted portfolio return calculations.

Development guide reference: Section 10.4.

The MVP uses end-of-day portfolio values and net external cash flow during each
day. Intraday cash-flow timing is intentionally not modeled.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from numbers import Real


class TimeWeightedReturnError(ValueError):
    """Raised when a daily TWR series cannot be calculated."""


@dataclass(frozen=True, slots=True)
class DailyPortfolioValue:
    """One end-of-day portfolio value and that day's signed external flow."""

    valuation_date: date
    portfolio_value: float
    net_external_flow: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "portfolio_value",
            _finite_real(
                self.portfolio_value,
                field_name="portfolio_value",
            ),
        )
        object.__setattr__(
            self,
            "net_external_flow",
            _finite_real(
                self.net_external_flow,
                field_name="net_external_flow",
            ),
        )


@dataclass(frozen=True, slots=True)
class DailyPortfolioReturn:
    """One canonical daily portfolio return."""

    valuation_date: date
    prior_portfolio_value: float
    ending_portfolio_value: float
    net_external_flow: float
    simple_return: float


@dataclass(frozen=True, slots=True)
class TimeWeightedReturnResult:
    """Chain-linked daily time-weighted return result."""

    period_start: date
    period_end: date
    daily_returns: tuple[DailyPortfolioReturn, ...]
    cumulative_return: float


def calculate_daily_time_weighted_return(
    values: Sequence[DailyPortfolioValue],
) -> TimeWeightedReturnResult:
    """Calculate canonical daily TWR using the Section 10.4 convention.

    For each day after the initial valuation:

    ``r_t = (V_t - CF_t) / V_(t-1) - 1``

    Deposits are positive external flows and withdrawals are negative. At least
    two strictly ascending daily valuations are required. The initial point is
    the starting valuation and therefore must not carry an external flow.
    """
    observations = tuple(values)

    if len(observations) < 2:
        raise TimeWeightedReturnError("daily TWR requires at least two portfolio valuations")

    if observations[0].net_external_flow != 0.0:
        raise TimeWeightedReturnError("the initial valuation must not carry an external cash flow")

    previous_date: date | None = None

    for observation in observations:
        if previous_date is not None and observation.valuation_date <= previous_date:
            raise TimeWeightedReturnError("valuation dates must be strictly ascending and unique")

        previous_date = observation.valuation_date

    daily_returns: list[DailyPortfolioReturn] = []
    growth_factor = 1.0

    for prior, current in zip(
        observations,
        observations[1:],
        strict=False,
    ):
        if prior.portfolio_value <= 0.0:
            raise TimeWeightedReturnError("prior portfolio value must be positive for daily TWR")

        simple_return = (
            current.portfolio_value - current.net_external_flow
        ) / prior.portfolio_value - 1.0

        if not math.isfinite(simple_return):
            raise TimeWeightedReturnError("daily portfolio return must be finite")

        growth_factor *= 1.0 + simple_return

        if not math.isfinite(growth_factor):
            raise TimeWeightedReturnError("chain-linked TWR growth factor must be finite")

        daily_returns.append(
            DailyPortfolioReturn(
                valuation_date=current.valuation_date,
                prior_portfolio_value=prior.portfolio_value,
                ending_portfolio_value=current.portfolio_value,
                net_external_flow=current.net_external_flow,
                simple_return=simple_return,
            )
        )

    return TimeWeightedReturnResult(
        period_start=observations[0].valuation_date,
        period_end=observations[-1].valuation_date,
        daily_returns=tuple(daily_returns),
        cumulative_return=growth_factor - 1.0,
    )


def _finite_real(
    value: object,
    *,
    field_name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
