"""Independent fixtures for volatility and Sharpe-ratio mathematics."""

import pytest

from portfolio_engine.performance.statistics import (
    annual_effective_rate_to_daily,
    annualized_volatility,
    sample_standard_deviation,
    sharpe_ratio,
)


def test_known_volatility_fixture_matches_independent_value() -> None:
    daily_returns = (-0.01, 0.0, 0.01)

    assert sample_standard_deviation(daily_returns) == pytest.approx(0.01)
    assert annualized_volatility(daily_returns) == pytest.approx(0.15874507866387544)


def test_known_five_percent_annual_rate_conversion_fixture() -> None:
    assert annual_effective_rate_to_daily(0.05) == pytest.approx(0.00019363050654397362)


def test_known_sharpe_fixture_matches_independent_value() -> None:
    result = sharpe_ratio(
        (0.001, 0.002, 0.003),
        risk_free_rate_annual=0.05,
    )

    assert result.value == pytest.approx(28.675226733470176)
