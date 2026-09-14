"""Unit tests for downside deviation and Sortino ratio."""

import math

import pytest

from portfolio_engine.config import (
    DEFAULT_MAR_ANNUAL,
    TRADING_DAYS_PER_YEAR,
)
from portfolio_engine.performance.downside import (
    SortinoRatioWarningCode,
    downside_deviation,
    sortino_ratio,
)


def test_default_mar_constant_is_zero() -> None:
    assert DEFAULT_MAR_ANNUAL == 0.0


def test_downside_deviation_uses_all_observations_in_denominator() -> None:
    result = downside_deviation((-0.02, 0.01, 0.03, -0.01))

    assert result == pytest.approx(0.011180339887498949)


def test_downside_deviation_is_zero_when_no_excess_return_is_negative() -> None:
    assert downside_deviation((0.01, 0.02, 0.03)) == 0.0


def test_downside_deviation_requires_an_observation() -> None:
    with pytest.raises(ValueError, match="at least one"):
        downside_deviation(())


def test_downside_deviation_rejects_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        downside_deviation((0.01, float("nan")))


def test_sortino_ratio_matches_known_zero_mar_fixture() -> None:
    result = sortino_ratio(
        (-0.02, 0.01, 0.03, -0.01),
        minimum_acceptable_return_annual=0.0,
    )

    assert result.value == pytest.approx(3.5496478698597693)
    assert result.downside_deviation == pytest.approx(0.011180339887498949)
    assert result.minimum_acceptable_return_daily == 0.0
    assert result.annualization_factor == TRADING_DAYS_PER_YEAR
    assert result.warnings == ()


def test_sortino_ratio_converts_annual_mar_to_daily_effective_rate() -> None:
    result = sortino_ratio(
        (-0.02, 0.01, 0.03, -0.01),
        minimum_acceptable_return_annual=0.05,
    )

    assert result.minimum_acceptable_return_daily == pytest.approx(0.00019363050654407988)
    assert result.value == pytest.approx(3.237087891111215)


def test_sortino_ratio_is_undefined_for_insufficient_observations() -> None:
    result = sortino_ratio(
        (-0.01,),
        minimum_acceptable_return_annual=0.0,
    )

    assert result.value is None
    assert result.downside_deviation is None
    assert result.warnings[0].code is SortinoRatioWarningCode.INSUFFICIENT_OBSERVATIONS


def test_sortino_ratio_is_undefined_for_zero_downside_deviation() -> None:
    result = sortino_ratio(
        (0.01, 0.02, 0.03),
        minimum_acceptable_return_annual=0.0,
    )

    assert result.value is None
    assert result.downside_deviation == 0.0
    assert result.warnings[0].code is SortinoRatioWarningCode.ZERO_DOWNSIDE_DEVIATION


def test_sortino_annualization_uses_sqrt_252() -> None:
    returns = (-0.02, 0.01, 0.03, -0.01)
    result = sortino_ratio(
        returns,
        minimum_acceptable_return_annual=0.0,
    )

    expected = (
        sum(returns) / len(returns) / downside_deviation(returns) * math.sqrt(TRADING_DAYS_PER_YEAR)
    )

    assert result.value == pytest.approx(expected)
