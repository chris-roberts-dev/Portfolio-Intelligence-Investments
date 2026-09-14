"""Independent validation fixtures for drawdown mathematics."""

import pytest

from portfolio_engine.performance.drawdown import (
    drawdown_series,
    maximum_drawdown,
    running_peak,
    wealth_index,
)


def test_manual_decline_recovery_path_matches_independent_values() -> None:
    returns = (0.20, -0.25, 0.10, 0.30)

    wealth = wealth_index(returns)
    peaks = running_peak(wealth)
    drawdowns = drawdown_series(wealth)
    result = maximum_drawdown(returns)

    expected_wealth = (1.0, 1.20, 0.90, 0.99, 1.287)
    expected_peaks = (1.0, 1.20, 1.20, 1.20, 1.287)
    expected_drawdowns = (0.0, 0.0, -0.25, -0.175, 0.0)

    assert wealth == pytest.approx(expected_wealth)
    assert peaks == pytest.approx(expected_peaks)
    assert drawdowns == pytest.approx(expected_drawdowns)

    assert result.value == pytest.approx(min(expected_drawdowns))
    assert result.peak_index == 1
    assert result.trough_index == 2
