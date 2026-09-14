"""Unit tests for annualized geometric and rolling cumulative returns."""

import math
from datetime import date

import pytest

from portfolio_engine.config import CALENDAR_DAYS_PER_YEAR
from portfolio_engine.performance.returns import (
    annualized_geometric_return,
    cagr,
    rolling_cumulative_returns,
)


def test_annualized_geometric_return_uses_elapsed_calendar_days() -> None:
    result = annualized_geometric_return(
        1.10,
        period_start=date(2025, 1, 1),
        period_end=date(2026, 1, 1),
    )
    expected = math.expm1(math.log(1.10) * CALENDAR_DAYS_PER_YEAR / 365)

    assert result.value == pytest.approx(expected)
    assert result.elapsed_days == 365
    assert result.elapsed_years == pytest.approx(365 / CALENDAR_DAYS_PER_YEAR)
    assert result.is_short_period


def test_period_longer_than_one_year_is_not_marked_short() -> None:
    result = annualized_geometric_return(
        1.10,
        period_start=date(2024, 1, 1),
        period_end=date(2025, 1, 1),
    )

    assert result.elapsed_days == 366
    assert not result.is_short_period


def test_cagr_derives_wealth_ratio_from_endpoint_values() -> None:
    result = cagr(
        100.0,
        121.0,
        period_start=date(2024, 1, 1),
        period_end=date(2025, 12, 31),
    )
    elapsed_days = 730
    expected = math.expm1(math.log(1.21) * CALENDAR_DAYS_PER_YEAR / elapsed_days)

    assert result.wealth_ratio == pytest.approx(1.21)
    assert result.value == pytest.approx(expected)


@pytest.mark.parametrize("wealth_ratio", [0.0, -1.0])
def test_annualized_geometric_return_rejects_nonpositive_wealth_ratio(
    wealth_ratio: float,
) -> None:
    with pytest.raises(ValueError, match="wealth_ratio"):
        annualized_geometric_return(
            wealth_ratio,
            period_start=date(2025, 1, 1),
            period_end=date(2026, 1, 1),
        )


@pytest.mark.parametrize(
    ("period_start", "period_end"),
    [
        (date(2025, 1, 1), date(2025, 1, 1)),
        (date(2025, 1, 2), date(2025, 1, 1)),
    ],
)
def test_annualized_geometric_return_requires_positive_elapsed_days(
    period_start: date,
    period_end: date,
) -> None:
    with pytest.raises(ValueError, match="period_end"):
        annualized_geometric_return(
            1.10,
            period_start=period_start,
            period_end=period_end,
        )


def test_known_two_period_rolling_returns() -> None:
    result = rolling_cumulative_returns((0.10, -0.10, 0.05), 2)

    assert result == pytest.approx((-0.01, -0.055))


def test_one_period_rolling_returns_equal_input_returns() -> None:
    returns = (0.10, -0.20, 0.05)

    assert rolling_cumulative_returns(returns, 1) == pytest.approx(returns)


def test_rolling_window_larger_than_series_returns_empty_tuple() -> None:
    assert rolling_cumulative_returns((0.10, 0.20), 3) == ()


@pytest.mark.parametrize("window_size", [0, -1])
def test_rolling_returns_reject_nonpositive_window_size(window_size: int) -> None:
    with pytest.raises(ValueError, match="window_size"):
        rolling_cumulative_returns((0.10, 0.20), window_size)


def test_rolling_returns_validate_entire_input_before_windowing() -> None:
    with pytest.raises(ValueError, match=r"returns\[1\]"):
        rolling_cumulative_returns((0.10, float("nan")), 3)
