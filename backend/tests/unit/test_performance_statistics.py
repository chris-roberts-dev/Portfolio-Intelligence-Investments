"""Unit tests for volatility and Sharpe-ratio calculations."""

import math

import pytest

from portfolio_engine.config import TRADING_DAYS_PER_YEAR
from portfolio_engine.performance.statistics import (
    SharpeRatioWarningCode,
    annual_effective_rate_to_daily,
    annualized_volatility,
    sample_standard_deviation,
    sharpe_ratio,
)


def test_sample_standard_deviation_uses_ddof_one() -> None:
    assert sample_standard_deviation((1.0, 2.0, 3.0)) == pytest.approx(1.0)


def test_sample_standard_deviation_requires_two_observations() -> None:
    with pytest.raises(ValueError, match="at least two"):
        sample_standard_deviation((0.01,))


def test_sample_standard_deviation_rejects_missing_or_nonfinite_values() -> None:
    with pytest.raises(TypeError):
        sample_standard_deviation((0.01, None))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="finite"):
        sample_standard_deviation((0.01, float("nan")))


def test_annualized_volatility_uses_sqrt_252() -> None:
    result = annualized_volatility((-0.01, 0.0, 0.01))

    assert result == pytest.approx(0.01 * math.sqrt(TRADING_DAYS_PER_YEAR))


def test_annual_effective_risk_free_rate_is_converted_to_daily() -> None:
    result = annual_effective_rate_to_daily(0.05)

    assert result == pytest.approx(0.00019363050654397362)


def test_annual_effective_rate_rejects_less_than_negative_one() -> None:
    with pytest.raises(ValueError, match="greater than or equal to -1"):
        annual_effective_rate_to_daily(-1.01)


def test_sharpe_ratio_uses_daily_excess_returns_and_sqrt_252() -> None:
    result = sharpe_ratio(
        (0.01, 0.02, 0.03),
        risk_free_rate_annual=0.0,
    )

    assert result.value == pytest.approx(2.0 * math.sqrt(TRADING_DAYS_PER_YEAR))
    assert result.risk_free_rate_daily == 0.0
    assert result.annualization_factor == TRADING_DAYS_PER_YEAR
    assert result.warnings == ()


def test_sharpe_ratio_is_undefined_for_insufficient_observations() -> None:
    result = sharpe_ratio(
        (0.01,),
        risk_free_rate_annual=0.0,
    )

    assert result.value is None
    assert result.warnings[0].code is SharpeRatioWarningCode.INSUFFICIENT_OBSERVATIONS


def test_sharpe_ratio_is_undefined_for_zero_excess_return_volatility() -> None:
    result = sharpe_ratio(
        (0.01, 0.01, 0.01),
        risk_free_rate_annual=0.0,
    )

    assert result.value is None
    assert result.warnings[0].code is SharpeRatioWarningCode.ZERO_EXCESS_RETURN_VOLATILITY
    assert "zero" in result.warnings[0].message.lower()
