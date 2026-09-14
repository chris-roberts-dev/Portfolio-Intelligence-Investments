"""Unit tests for wealth-index and drawdown calculations."""

import pytest

from portfolio_engine.performance.drawdown import (
    MaximumDrawdownWarningCode,
    drawdown_series,
    maximum_drawdown,
    running_peak,
    wealth_index,
)


def test_monotonic_growth_has_zero_drawdown() -> None:
    wealth = wealth_index((0.10, 0.05, 0.20))

    assert wealth == pytest.approx((1.0, 1.10, 1.155, 1.386))
    assert running_peak(wealth) == pytest.approx(wealth)
    assert drawdown_series(wealth) == pytest.approx((0.0, 0.0, 0.0, 0.0))

    result = maximum_drawdown((0.10, 0.05, 0.20))

    assert result.value == 0.0
    assert result.peak_index == 0
    assert result.trough_index == 0


def test_decline_and_recovery_fixture_tracks_peak_and_trough() -> None:
    returns = (0.20, -0.25, 0.10, 0.30)
    wealth = wealth_index(returns)

    assert wealth == pytest.approx((1.0, 1.20, 0.90, 0.99, 1.287))
    assert running_peak(wealth) == pytest.approx((1.0, 1.20, 1.20, 1.20, 1.287))
    assert drawdown_series(wealth) == pytest.approx((0.0, 0.0, -0.25, -0.175, 0.0))

    result = maximum_drawdown(returns)

    assert result.value == pytest.approx(-0.25)
    assert result.peak_index == 1
    assert result.trough_index == 2


def test_first_period_loss_uses_initial_wealth_as_peak() -> None:
    result = maximum_drawdown((-0.20, 0.10))

    assert result.value == pytest.approx(-0.20)
    assert result.peak_index == 0
    assert result.trough_index == 1


def test_total_loss_produces_negative_one_drawdown() -> None:
    wealth = wealth_index((-1.0, 0.50))

    assert wealth == (1.0, 0.0, 0.0)
    assert drawdown_series(wealth) == (0.0, -1.0, -1.0)

    result = maximum_drawdown((-1.0, 0.50))

    assert result.value == -1.0
    assert result.peak_index == 0
    assert result.trough_index == 1


def test_empty_returns_have_baseline_wealth_but_undefined_maximum_drawdown() -> None:
    assert wealth_index(()) == (1.0,)

    result = maximum_drawdown(())

    assert result.value is None
    assert result.peak_index is None
    assert result.trough_index is None
    assert result.warnings[0].code is MaximumDrawdownWarningCode.INSUFFICIENT_OBSERVATIONS


def test_empty_wealth_sequences_are_handled_explicitly() -> None:
    assert running_peak(()) == ()
    assert drawdown_series(()) == ()


def test_returns_below_negative_one_are_rejected() -> None:
    with pytest.raises(ValueError, match="greater than or equal to -1"):
        wealth_index((-1.01,))


def test_missing_and_nonfinite_returns_are_not_silently_dropped() -> None:
    with pytest.raises(TypeError):
        wealth_index((0.10, None))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="finite"):
        wealth_index((0.10, float("nan")))
