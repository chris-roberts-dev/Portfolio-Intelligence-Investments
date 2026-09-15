"""Unit tests for canonical daily time-weighted return."""

from datetime import date

import pytest

from portfolio_engine.performance.time_weighted import (
    DailyPortfolioValue,
    TimeWeightedReturnError,
    calculate_daily_time_weighted_return,
)


def test_daily_twr_neutralizes_deposit() -> None:
    result = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=100.0,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=150.0,
                net_external_flow=50.0,
            ),
        )
    )

    assert result.daily_returns[0].simple_return == pytest.approx(0.0)
    assert result.cumulative_return == pytest.approx(0.0)


def test_daily_twr_neutralizes_withdrawal() -> None:
    result = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=100.0,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=60.0,
                net_external_flow=-40.0,
            ),
        )
    )

    assert result.daily_returns[0].simple_return == pytest.approx(0.0)
    assert result.cumulative_return == pytest.approx(0.0)


def test_daily_twr_uses_normative_external_flow_formula() -> None:
    result = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=100.0,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=120.0,
                net_external_flow=10.0,
            ),
        )
    )

    assert result.daily_returns[0].simple_return == pytest.approx(0.10)


def test_daily_twr_chain_links_daily_returns() -> None:
    result = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=100.0,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=110.0,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 6),
                portfolio_value=104.5,
            ),
        )
    )

    assert tuple(item.simple_return for item in result.daily_returns) == pytest.approx(
        (0.10, -0.05)
    )
    assert result.cumulative_return == pytest.approx(0.045)


def test_daily_twr_requires_positive_prior_value() -> None:
    with pytest.raises(
        TimeWeightedReturnError,
        match="prior portfolio value",
    ):
        calculate_daily_time_weighted_return(
            (
                DailyPortfolioValue(
                    valuation_date=date(2026, 1, 2),
                    portfolio_value=0.0,
                ),
                DailyPortfolioValue(
                    valuation_date=date(2026, 1, 5),
                    portfolio_value=100.0,
                ),
            )
        )


def test_daily_twr_rejects_nonzero_flow_on_initial_valuation() -> None:
    with pytest.raises(
        TimeWeightedReturnError,
        match="initial valuation",
    ):
        calculate_daily_time_weighted_return(
            (
                DailyPortfolioValue(
                    valuation_date=date(2026, 1, 2),
                    portfolio_value=100.0,
                    net_external_flow=100.0,
                ),
                DailyPortfolioValue(
                    valuation_date=date(2026, 1, 5),
                    portfolio_value=100.0,
                ),
            )
        )


def test_daily_twr_rejects_duplicate_or_unsorted_dates() -> None:
    with pytest.raises(
        TimeWeightedReturnError,
        match="strictly ascending",
    ):
        calculate_daily_time_weighted_return(
            (
                DailyPortfolioValue(
                    valuation_date=date(2026, 1, 5),
                    portfolio_value=100.0,
                ),
                DailyPortfolioValue(
                    valuation_date=date(2026, 1, 5),
                    portfolio_value=110.0,
                ),
            )
        )
