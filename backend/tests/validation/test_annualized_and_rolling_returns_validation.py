"""Independent fixtures for annualized geometric and rolling returns."""

import math
from datetime import date

import pytest

from portfolio_engine.config import CALENDAR_DAYS_PER_YEAR
from portfolio_engine.performance.returns import (
    annualized_geometric_return,
    rolling_cumulative_returns,
)


def test_calendar_day_annualization_matches_independent_fixture() -> None:
    wealth_ratio = 1.25
    elapsed_days = 366
    expected = wealth_ratio ** (CALENDAR_DAYS_PER_YEAR / elapsed_days) - 1.0

    result = annualized_geometric_return(
        wealth_ratio,
        period_start=date(2020, 1, 1),
        period_end=date(2021, 1, 1),
    )

    assert result.elapsed_days == elapsed_days
    assert math.isclose(result.value, expected, rel_tol=1e-12, abs_tol=1e-12)


def test_three_period_rolling_fixture_matches_manual_compounding() -> None:
    returns = (0.10, -0.05, 0.20, -0.10)

    result = rolling_cumulative_returns(returns, 3)

    assert result == pytest.approx((0.254, 0.026))
