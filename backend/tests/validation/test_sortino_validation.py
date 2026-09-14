"""Independent numerical validation for downside deviation and Sortino ratio."""

import math
from statistics import fmean

import pytest

from portfolio_engine.config import TRADING_DAYS_PER_YEAR
from portfolio_engine.performance.downside import (
    downside_deviation,
    sortino_ratio,
)
from portfolio_engine.performance.statistics import annual_effective_rate_to_daily


def test_known_downside_deviation_fixture_matches_manual_calculation() -> None:
    excess_returns = (-0.02, 0.01, 0.03, -0.01)
    expected = math.sqrt(((-0.02) ** 2 + 0.0**2 + 0.0**2 + (-0.01) ** 2) / 4)

    assert downside_deviation(excess_returns) == pytest.approx(expected)


def test_known_sortino_fixture_matches_independent_calculation() -> None:
    daily_returns = (-0.02, 0.01, 0.03, -0.01)
    mar_annual = 0.05
    mar_daily = annual_effective_rate_to_daily(mar_annual)
    excess_returns = tuple(daily_return - mar_daily for daily_return in daily_returns)
    negative_returns = tuple(min(excess_return, 0.0) for excess_return in excess_returns)
    expected_downside = math.sqrt(
        sum(value**2 for value in negative_returns) / len(negative_returns)
    )
    expected_sortino = fmean(excess_returns) / expected_downside * math.sqrt(TRADING_DAYS_PER_YEAR)

    result = sortino_ratio(
        daily_returns,
        minimum_acceptable_return_annual=mar_annual,
    )

    assert result.minimum_acceptable_return_daily == pytest.approx(mar_daily)
    assert result.downside_deviation == pytest.approx(expected_downside)
    assert result.value == pytest.approx(expected_sortino)
