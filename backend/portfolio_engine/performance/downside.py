"""Canonical downside-deviation and Sortino-ratio calculations.

Development guide reference: Section 11.8.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real
from statistics import fmean

from portfolio_engine.config import TRADING_DAYS_PER_YEAR
from portfolio_engine.performance.statistics import annual_effective_rate_to_daily


class SortinoRatioWarningCode(StrEnum):
    """Stable warning codes for undefined Sortino-ratio results."""

    INSUFFICIENT_OBSERVATIONS = "INSUFFICIENT_OBSERVATIONS"
    ZERO_DOWNSIDE_DEVIATION = "ZERO_DOWNSIDE_DEVIATION"
    NON_FINITE_RESULT = "NON_FINITE_RESULT"


@dataclass(frozen=True, slots=True)
class SortinoRatioWarning:
    """One explanatory warning attached to a Sortino-ratio result."""

    code: SortinoRatioWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class SortinoRatioResult:
    """Typed annualized Sortino-ratio result and explicit MAR assumptions."""

    value: float | None
    observations: int
    minimum_acceptable_return_annual: float
    minimum_acceptable_return_daily: float
    downside_deviation: float | None
    annualization_factor: int
    warnings: tuple[SortinoRatioWarning, ...] = ()


def downside_deviation(excess_returns: Sequence[float]) -> float:
    """Return downside deviation of period-aligned excess returns.

    Each downside observation is ``min(excess_t, 0)`` and the deviation is
    ``sqrt(mean(negative_t ** 2))``. At least one finite observation is
    required. Missing observations must be handled by the caller.
    """
    normalized = _validated_finite_values(
        excess_returns,
        field_name="excess_returns",
    )

    if not normalized:
        raise ValueError("downside deviation requires at least one observation")

    negative_returns = tuple(min(excess_return, 0.0) for excess_return in normalized)
    result = math.hypot(*negative_returns) / math.sqrt(len(negative_returns))

    if not math.isfinite(result):
        raise ValueError("downside deviation must be finite")

    return result


def sortino_ratio(
    daily_returns: Sequence[float],
    *,
    minimum_acceptable_return_annual: float,
) -> SortinoRatioResult:
    """Return annualized Sortino ratio from daily period-aligned excess returns.

    The annual minimum acceptable return is explicit and converted to a daily
    effective rate before subtraction. Fewer than two observations or zero
    downside deviation produce ``value=None`` with an explanatory warning.
    """
    normalized_returns = _validated_finite_values(
        daily_returns,
        field_name="daily_returns",
    )
    normalized_mar = _finite_real(
        minimum_acceptable_return_annual,
        field_name="minimum_acceptable_return_annual",
    )
    minimum_acceptable_return_daily = annual_effective_rate_to_daily(normalized_mar)
    observations = len(normalized_returns)

    if observations < 2:
        return _undefined_sortino_result(
            observations=observations,
            minimum_acceptable_return_annual=normalized_mar,
            minimum_acceptable_return_daily=minimum_acceptable_return_daily,
            downside_deviation_value=None,
            code=SortinoRatioWarningCode.INSUFFICIENT_OBSERVATIONS,
            message="Sortino ratio requires at least two valid daily observations.",
        )

    excess_returns = tuple(
        daily_return - minimum_acceptable_return_daily for daily_return in normalized_returns
    )
    downside_deviation_value = downside_deviation(excess_returns)

    if downside_deviation_value == 0.0:
        return _undefined_sortino_result(
            observations=observations,
            minimum_acceptable_return_annual=normalized_mar,
            minimum_acceptable_return_daily=minimum_acceptable_return_daily,
            downside_deviation_value=downside_deviation_value,
            code=SortinoRatioWarningCode.ZERO_DOWNSIDE_DEVIATION,
            message=("Sortino ratio is undefined because downside deviation is zero."),
        )

    value = fmean(excess_returns) / downside_deviation_value * math.sqrt(TRADING_DAYS_PER_YEAR)

    if not math.isfinite(value):
        return _undefined_sortino_result(
            observations=observations,
            minimum_acceptable_return_annual=normalized_mar,
            minimum_acceptable_return_daily=minimum_acceptable_return_daily,
            downside_deviation_value=downside_deviation_value,
            code=SortinoRatioWarningCode.NON_FINITE_RESULT,
            message="Sortino ratio is undefined because the result is non-finite.",
        )

    return SortinoRatioResult(
        value=value,
        observations=observations,
        minimum_acceptable_return_annual=normalized_mar,
        minimum_acceptable_return_daily=minimum_acceptable_return_daily,
        downside_deviation=downside_deviation_value,
        annualization_factor=TRADING_DAYS_PER_YEAR,
    )


def _undefined_sortino_result(
    *,
    observations: int,
    minimum_acceptable_return_annual: float,
    minimum_acceptable_return_daily: float,
    downside_deviation_value: float | None,
    code: SortinoRatioWarningCode,
    message: str,
) -> SortinoRatioResult:
    return SortinoRatioResult(
        value=None,
        observations=observations,
        minimum_acceptable_return_annual=minimum_acceptable_return_annual,
        minimum_acceptable_return_daily=minimum_acceptable_return_daily,
        downside_deviation=downside_deviation_value,
        annualization_factor=TRADING_DAYS_PER_YEAR,
        warnings=(
            SortinoRatioWarning(
                code=code,
                message=message,
            ),
        ),
    )


def _validated_finite_values(
    values: Sequence[float],
    *,
    field_name: str,
) -> tuple[float, ...]:
    return tuple(
        _finite_real(
            value,
            field_name=f"{field_name}[{index}]",
        )
        for index, value in enumerate(values)
    )


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
