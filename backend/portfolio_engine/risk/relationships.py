"""Canonical paired-return covariance, beta, and correlation calculations.

Pairwise statistics use explicitly dated valid observations. Asset and
benchmark series are validated independently, then aligned on the intersection
of their dates without filling or fabricating observations.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from numbers import Real
from statistics import fmean

from portfolio_engine.config import MIN_BETA_OBS


@dataclass(frozen=True, slots=True)
class ReturnObservation:
    """One finite return observation associated with an explicit date."""

    trade_date: date
    value: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _finite_real(self.value, field_name="value"),
        )


@dataclass(frozen=True, slots=True)
class AlignedReturnObservation:
    """One explicitly aligned asset/benchmark return pair."""

    trade_date: date
    asset_return: float
    benchmark_return: float


type AlignedReturnSeries = tuple[AlignedReturnObservation, ...]


class ReturnAlignmentError(ValueError):
    """Raised when a dated return series violates alignment prerequisites."""


class RelationshipWarningCode(StrEnum):
    """Stable warning codes for undefined beta or correlation results."""

    INSUFFICIENT_OBSERVATIONS = "INSUFFICIENT_OBSERVATIONS"
    ZERO_BENCHMARK_VARIANCE = "ZERO_BENCHMARK_VARIANCE"
    ZERO_ASSET_VARIANCE = "ZERO_ASSET_VARIANCE"
    NON_FINITE_RESULT = "NON_FINITE_RESULT"


@dataclass(frozen=True, slots=True)
class RelationshipWarning:
    """One explanatory warning attached to a relationship statistic."""

    code: RelationshipWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class BetaResult:
    """Typed beta result for explicitly aligned paired returns."""

    value: float | None
    observations: int
    warnings: tuple[RelationshipWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Typed Pearson-correlation result for explicitly aligned paired returns."""

    value: float | None
    observations: int
    warnings: tuple[RelationshipWarning, ...] = ()


def align_return_observations(
    asset_returns: Sequence[ReturnObservation],
    benchmark_returns: Sequence[ReturnObservation],
) -> AlignedReturnSeries:
    """Align valid asset and benchmark observations on their date intersection.

    Each input must be strictly ascending with unique dates. Dates present in
    only one series are excluded from the paired result; no observation is
    filled, fabricated, forward-filled, or otherwise rewritten.
    """
    validated_asset = _validated_observation_sequence(
        asset_returns,
        series_name="asset_returns",
    )
    validated_benchmark = _validated_observation_sequence(
        benchmark_returns,
        series_name="benchmark_returns",
    )
    benchmark_by_date = {observation.trade_date: observation for observation in validated_benchmark}

    return tuple(
        AlignedReturnObservation(
            trade_date=asset_observation.trade_date,
            asset_return=asset_observation.value,
            benchmark_return=benchmark_by_date[asset_observation.trade_date].value,
        )
        for asset_observation in validated_asset
        if asset_observation.trade_date in benchmark_by_date
    )


def sample_covariance(
    asset_returns: Sequence[ReturnObservation],
    benchmark_returns: Sequence[ReturnObservation],
) -> float:
    """Return sample covariance over intersecting valid dates using ``ddof=1``."""
    aligned = align_return_observations(
        asset_returns,
        benchmark_returns,
    )

    if len(aligned) < 2:
        raise ValueError("sample covariance requires at least two paired observations")

    result = _sample_covariance_from_aligned(aligned)

    if not math.isfinite(result):
        raise ValueError("sample covariance must be finite")

    return result


def beta(
    asset_returns: Sequence[ReturnObservation],
    benchmark_returns: Sequence[ReturnObservation],
) -> BetaResult:
    """Return asset beta when sufficient intersecting benchmark history exists."""
    aligned = align_return_observations(
        asset_returns,
        benchmark_returns,
    )
    observations = len(aligned)

    if observations < MIN_BETA_OBS:
        return _undefined_beta(
            observations=observations,
            code=RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS,
            message=(f"Beta requires at least {MIN_BETA_OBS} paired return observations."),
        )

    benchmark_values = tuple(observation.benchmark_return for observation in aligned)
    benchmark_variance = _sample_variance(benchmark_values)

    if benchmark_variance == 0.0:
        return _undefined_beta(
            observations=observations,
            code=RelationshipWarningCode.ZERO_BENCHMARK_VARIANCE,
            message=("Beta is undefined because benchmark sample variance is zero."),
        )

    covariance = _sample_covariance_from_aligned(aligned)
    value = covariance / benchmark_variance

    if not math.isfinite(value):
        return _undefined_beta(
            observations=observations,
            code=RelationshipWarningCode.NON_FINITE_RESULT,
            message="Beta is undefined because the computed value is non-finite.",
        )

    return BetaResult(
        value=value,
        observations=observations,
    )


def pearson_correlation(
    asset_returns: Sequence[ReturnObservation],
    benchmark_returns: Sequence[ReturnObservation],
) -> CorrelationResult:
    """Return Pearson correlation over intersecting valid paired dates."""
    aligned = align_return_observations(
        asset_returns,
        benchmark_returns,
    )
    observations = len(aligned)

    if observations < 2:
        return _undefined_correlation(
            observations=observations,
            code=RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS,
            message=("Correlation requires at least two paired return observations."),
        )

    asset_values = tuple(observation.asset_return for observation in aligned)
    benchmark_values = tuple(observation.benchmark_return for observation in aligned)
    asset_variance = _sample_variance(asset_values)
    benchmark_variance = _sample_variance(benchmark_values)

    if asset_variance == 0.0:
        return _undefined_correlation(
            observations=observations,
            code=RelationshipWarningCode.ZERO_ASSET_VARIANCE,
            message=("Correlation is undefined because asset sample variance is zero."),
        )

    if benchmark_variance == 0.0:
        return _undefined_correlation(
            observations=observations,
            code=RelationshipWarningCode.ZERO_BENCHMARK_VARIANCE,
            message=("Correlation is undefined because benchmark sample variance is zero."),
        )

    covariance = _sample_covariance_from_aligned(aligned)
    value = covariance / math.sqrt(asset_variance * benchmark_variance)

    if not math.isfinite(value):
        return _undefined_correlation(
            observations=observations,
            code=RelationshipWarningCode.NON_FINITE_RESULT,
            message=("Correlation is undefined because the computed value is non-finite."),
        )

    return CorrelationResult(
        value=value,
        observations=observations,
    )


def _sample_covariance_from_aligned(
    aligned: AlignedReturnSeries,
) -> float:
    asset_mean = fmean(observation.asset_return for observation in aligned)
    benchmark_mean = fmean(observation.benchmark_return for observation in aligned)
    numerator = math.fsum(
        (observation.asset_return - asset_mean) * (observation.benchmark_return - benchmark_mean)
        for observation in aligned
    )

    return numerator / (len(aligned) - 1)


def _sample_variance(values: tuple[float, ...]) -> float:
    mean = fmean(values)

    return math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _validated_observation_sequence(
    observations: Sequence[ReturnObservation],
    *,
    series_name: str,
) -> tuple[ReturnObservation, ...]:
    validated = tuple(observations)
    previous_date: date | None = None

    for index, observation in enumerate(validated):
        if not isinstance(observation, ReturnObservation):
            raise TypeError(f"{series_name}[{index}] must be a ReturnObservation")

        if previous_date is not None:
            if observation.trade_date == previous_date:
                raise ReturnAlignmentError(f"{series_name} must not contain duplicate dates")

            if observation.trade_date < previous_date:
                raise ReturnAlignmentError(f"{series_name} must be strictly ascending by date")

        previous_date = observation.trade_date

    return validated


def _undefined_beta(
    *,
    observations: int,
    code: RelationshipWarningCode,
    message: str,
) -> BetaResult:
    return BetaResult(
        value=None,
        observations=observations,
        warnings=(
            RelationshipWarning(
                code=code,
                message=message,
            ),
        ),
    )


def _undefined_correlation(
    *,
    observations: int,
    code: RelationshipWarningCode,
    message: str,
) -> CorrelationResult:
    return CorrelationResult(
        value=None,
        observations=observations,
        warnings=(
            RelationshipWarning(
                code=code,
                message=message,
            ),
        ),
    )


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
