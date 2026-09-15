"""Independent numerical validation for daily time-weighted return."""

from datetime import date

import pytest

from portfolio_engine.performance.time_weighted import (
    DailyPortfolioValue,
    calculate_daily_time_weighted_return,
)


def test_known_daily_twr_fixture_matches_manual_chain_linking() -> None:
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
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 6),
                portfolio_value=126.0,
            ),
        )
    )

    first_daily_return = (120.0 - 10.0) / 100.0 - 1.0
    second_daily_return = 126.0 / 120.0 - 1.0
    expected = (1.0 + first_daily_return) * (1.0 + second_daily_return) - 1.0

    assert first_daily_return == pytest.approx(0.10)
    assert second_daily_return == pytest.approx(0.05)
    assert expected == pytest.approx(0.155)
    assert result.cumulative_return == pytest.approx(expected)
