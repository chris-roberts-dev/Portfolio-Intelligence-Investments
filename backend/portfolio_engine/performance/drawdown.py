"""Canonical wealth-index and drawdown calculations.

The calculations in this module operate only on observations supplied by the
caller. Running peaks and drawdowns at each position use no future observations.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real

type WealthIndex = tuple[float, ...]
type DrawdownSeries = tuple[float, ...]


class MaximumDrawdownWarningCode(StrEnum):
    """Stable warning codes for undefined maximum-drawdown results."""

    INSUFFICIENT_OBSERVATIONS = "INSUFFICIENT_OBSERVATIONS"


@dataclass(frozen=True, slots=True)
class MaximumDrawdownWarning:
    """One explanatory warning attached to a maximum-drawdown result."""

    code: MaximumDrawdownWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class MaximumDrawdownResult:
    """Maximum drawdown and its locations in the normalized wealth index."""

    value: float | None
    observations: int
    peak_index: int | None
    trough_index: int | None
    warnings: tuple[MaximumDrawdownWarning, ...] = ()


def wealth_index(simple_return_series: Sequence[float]) -> WealthIndex:
    """Build a normalized wealth index beginning at 1.0.

    N simple-return observations produce N+1 wealth observations. Returns below
    -100% are invalid because they imply negative wealth.
    """
    normalized_returns = _validated_simple_returns(simple_return_series)
    return _wealth_index_from_validated_returns(normalized_returns)


def running_peak(wealth_values: Sequence[float]) -> WealthIndex:
    """Return the running maximum using only observations through each point."""
    normalized_wealth = _validated_wealth_values(wealth_values)

    if not normalized_wealth:
        return ()

    peaks: list[float] = []
    current_peak = normalized_wealth[0]

    for wealth in normalized_wealth:
        current_peak = max(current_peak, wealth)
        peaks.append(current_peak)

    return tuple(peaks)


def drawdown_series(wealth_values: Sequence[float]) -> DrawdownSeries:
    """Return point-in-time drawdowns relative to each running wealth peak."""
    normalized_wealth = _validated_wealth_values(wealth_values)

    if not normalized_wealth:
        return ()

    peaks = running_peak(normalized_wealth)
    drawdowns: list[float] = []

    for wealth, peak in zip(normalized_wealth, peaks, strict=True):
        drawdown = wealth / peak - 1.0

        if not math.isfinite(drawdown):
            raise ValueError("drawdown must be finite")

        drawdowns.append(drawdown)

    return tuple(drawdowns)


def maximum_drawdown(
    simple_return_series: Sequence[float],
) -> MaximumDrawdownResult:
    """Return maximum drawdown with peak/trough wealth-index locations.

    Peak and trough indices refer to the normalized wealth index, whose index 0
    is the initial wealth point before the first supplied return.
    """
    normalized_returns = _validated_simple_returns(simple_return_series)
    observations = len(normalized_returns)

    if observations == 0:
        return MaximumDrawdownResult(
            value=None,
            observations=0,
            peak_index=None,
            trough_index=None,
            warnings=(
                MaximumDrawdownWarning(
                    code=(MaximumDrawdownWarningCode.INSUFFICIENT_OBSERVATIONS),
                    message=("Maximum drawdown requires at least one return observation."),
                ),
            ),
        )

    wealth = _wealth_index_from_validated_returns(normalized_returns)
    drawdowns = drawdown_series(wealth)

    current_peak_index = 0
    maximum_drawdown_value = 0.0
    maximum_drawdown_peak_index = 0
    maximum_drawdown_trough_index = 0

    for index in range(1, len(wealth)):
        if wealth[index] > wealth[current_peak_index]:
            current_peak_index = index

        if drawdowns[index] < maximum_drawdown_value:
            maximum_drawdown_value = drawdowns[index]
            maximum_drawdown_peak_index = current_peak_index
            maximum_drawdown_trough_index = index

    return MaximumDrawdownResult(
        value=maximum_drawdown_value,
        observations=observations,
        peak_index=maximum_drawdown_peak_index,
        trough_index=maximum_drawdown_trough_index,
    )


def _wealth_index_from_validated_returns(
    normalized_returns: tuple[float, ...],
) -> WealthIndex:
    wealth = 1.0
    values = [wealth]

    for period_return in normalized_returns:
        wealth *= 1.0 + period_return

        if not math.isfinite(wealth):
            raise ValueError("wealth index must remain finite")

        values.append(wealth)

    return tuple(values)


def _validated_simple_returns(
    values: Sequence[float],
) -> tuple[float, ...]:
    normalized: list[float] = []

    for index, value in enumerate(values):
        period_return = _finite_real(
            value,
            field_name=f"simple_return_series[{index}]",
        )

        if period_return < -1.0:
            raise ValueError(f"simple_return_series[{index}] must be greater than or equal to -1")

        normalized.append(period_return)

    return tuple(normalized)


def _validated_wealth_values(
    values: Sequence[float],
) -> WealthIndex:
    normalized: list[float] = []

    for index, value in enumerate(values):
        wealth = _finite_real(
            value,
            field_name=f"wealth_values[{index}]",
        )

        if wealth < 0.0:
            raise ValueError(f"wealth_values[{index}] must not be negative")

        normalized.append(wealth)

    if normalized and normalized[0] <= 0.0:
        raise ValueError("wealth_values[0] must be positive")

    return tuple(normalized)


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
