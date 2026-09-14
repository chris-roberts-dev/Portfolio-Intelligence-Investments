"""Canonical volatility and Sharpe-ratio calculations.

Development guide references: Sections 11.5, 11.6, and 11.7.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real
from statistics import fmean, stdev

from portfolio_engine.config import TRADING_DAYS_PER_YEAR


class SharpeRatioWarningCode(StrEnum):
    """Stable warning codes for undefined Sharpe-ratio results."""

    INSUFFICIENT_OBSERVATIONS = "INSUFFICIENT_OBSERVATIONS"
    ZERO_EXCESS_RETURN_VOLATILITY = "ZERO_EXCESS_RETURN_VOLATILITY"
    NON_FINITE_RESULT = "NON_FINITE_RESULT"


@dataclass(frozen=True, slots=True)
class SharpeRatioWarning:
    """One explanatory warning attached to a Sharpe-ratio result."""

    code: SharpeRatioWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class SharpeRatioResult:
    """Typed annualized Sharpe-ratio result and its explicit assumptions."""

    value: float | None
    observations: int
    risk_free_rate_annual: float
    risk_free_rate_daily: float
    annualization_factor: int
    warnings: tuple[SharpeRatioWarning, ...] = ()


def sample_standard_deviation(values: Sequence[float]) -> float:
    """Return sample standard deviation using the NORMATIVE ``ddof=1`` rule.

    At least two finite observations are required. Missing or non-finite values
    must be resolved by the caller rather than silently dropped or replaced.
    """
    normalized = _validated_finite_values(values, field_name="values")

    if len(normalized) < 2:
        raise ValueError("sample standard deviation requires at least two observations")

    result = float(stdev(normalized))

    if not math.isfinite(result):
        raise ValueError("sample standard deviation must be finite")

    return result


def annualized_volatility(daily_returns: Sequence[float]) -> float:
    """Annualize daily simple-return sample volatility with ``sqrt(252)``.

    The input must contain at least two finite daily simple-return observations.
    """
    daily_standard_deviation = sample_standard_deviation(daily_returns)
    result = daily_standard_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)

    if not math.isfinite(result):
        raise ValueError("annualized volatility must be finite")

    return result


def annual_effective_rate_to_daily(rate_annual: float) -> float:
    """Convert an annual effective rate to a daily effective rate over 252 periods."""
    normalized = _finite_real(rate_annual, field_name="rate_annual")

    if normalized < -1.0:
        raise ValueError("rate_annual must be greater than or equal to -1")

    if normalized == -1.0:
        return -1.0

    result = math.expm1(math.log1p(normalized) / TRADING_DAYS_PER_YEAR)

    if not math.isfinite(result):
        raise ValueError("daily effective rate must be finite")

    return result


def sharpe_ratio(
    daily_returns: Sequence[float],
    *,
    risk_free_rate_annual: float,
) -> SharpeRatioResult:
    """Return annualized Sharpe ratio from daily period-aligned excess returns.

    The risk-free input is an explicit annual effective rate and is converted to
    a daily effective rate before subtraction. Fewer than two observations or
    zero excess-return sample standard deviation produce ``value=None`` with an
    explanatory warning rather than NaN or infinity.
    """
    normalized_returns = _validated_finite_values(
        daily_returns,
        field_name="daily_returns",
    )
    normalized_risk_free_rate = _finite_real(
        risk_free_rate_annual,
        field_name="risk_free_rate_annual",
    )
    risk_free_rate_daily = annual_effective_rate_to_daily(normalized_risk_free_rate)
    observations = len(normalized_returns)

    if observations < 2:
        return _undefined_sharpe_result(
            observations=observations,
            risk_free_rate_annual=normalized_risk_free_rate,
            risk_free_rate_daily=risk_free_rate_daily,
            code=SharpeRatioWarningCode.INSUFFICIENT_OBSERVATIONS,
            message="Sharpe ratio requires at least two valid daily return observations.",
        )

    excess_returns = tuple(
        daily_return - risk_free_rate_daily for daily_return in normalized_returns
    )
    excess_standard_deviation = sample_standard_deviation(excess_returns)

    if excess_standard_deviation == 0.0:
        return _undefined_sharpe_result(
            observations=observations,
            risk_free_rate_annual=normalized_risk_free_rate,
            risk_free_rate_daily=risk_free_rate_daily,
            code=SharpeRatioWarningCode.ZERO_EXCESS_RETURN_VOLATILITY,
            message=(
                "Sharpe ratio is undefined because excess-return sample standard deviation is zero."
            ),
        )

    value = fmean(excess_returns) / excess_standard_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)

    if not math.isfinite(value):
        return _undefined_sharpe_result(
            observations=observations,
            risk_free_rate_annual=normalized_risk_free_rate,
            risk_free_rate_daily=risk_free_rate_daily,
            code=SharpeRatioWarningCode.NON_FINITE_RESULT,
            message="Sharpe ratio is undefined because the computed value is non-finite.",
        )

    return SharpeRatioResult(
        value=value,
        observations=observations,
        risk_free_rate_annual=normalized_risk_free_rate,
        risk_free_rate_daily=risk_free_rate_daily,
        annualization_factor=TRADING_DAYS_PER_YEAR,
    )


def _undefined_sharpe_result(
    *,
    observations: int,
    risk_free_rate_annual: float,
    risk_free_rate_daily: float,
    code: SharpeRatioWarningCode,
    message: str,
) -> SharpeRatioResult:
    return SharpeRatioResult(
        value=None,
        observations=observations,
        risk_free_rate_annual=risk_free_rate_annual,
        risk_free_rate_daily=risk_free_rate_daily,
        annualization_factor=TRADING_DAYS_PER_YEAR,
        warnings=(SharpeRatioWarning(code=code, message=message),),
    )


def _validated_finite_values(
    values: Sequence[float],
    *,
    field_name: str,
) -> tuple[float, ...]:
    return tuple(
        _finite_real(value, field_name=f"{field_name}[{index}]")
        for index, value in enumerate(values)
    )


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
