"""Unit tests for paired-return covariance, beta, and correlation."""

from datetime import date, timedelta

import pytest

from portfolio_engine.config import MIN_BETA_OBS
from portfolio_engine.risk.relationships import (
    RelationshipWarningCode,
    ReturnAlignmentError,
    ReturnObservation,
    align_return_observations,
    beta,
    pearson_correlation,
    sample_covariance,
)


def observations(
    values: tuple[float, ...],
    *,
    start: date = date(2025, 1, 1),
) -> tuple[ReturnObservation, ...]:
    return tuple(
        ReturnObservation(
            trade_date=start + timedelta(days=index),
            value=value,
        )
        for index, value in enumerate(values)
    )


def linear_beta_observations(
    count: int,
) -> tuple[
    tuple[ReturnObservation, ...],
    tuple[ReturnObservation, ...],
]:
    benchmark_values = tuple((index + 1) / 1000.0 for index in range(count))
    asset_values = tuple(0.001 + 2.0 * benchmark_value for benchmark_value in benchmark_values)

    return (
        observations(asset_values),
        observations(benchmark_values),
    )


def test_alignment_preserves_matching_dates_and_values() -> None:
    asset = observations((0.01, 0.02, 0.03))
    benchmark = observations((0.005, 0.01, 0.015))

    aligned = align_return_observations(
        asset,
        benchmark,
    )

    assert tuple(item.trade_date for item in aligned) == tuple(item.trade_date for item in asset)
    assert tuple(item.asset_return for item in aligned) == (0.01, 0.02, 0.03)
    assert tuple(item.benchmark_return for item in aligned) == (
        0.005,
        0.01,
        0.015,
    )


def test_alignment_uses_intersection_of_valid_dates() -> None:
    asset = observations((0.01, 0.02, 0.03))
    benchmark = (
        ReturnObservation(date(2025, 1, 1), 0.005),
        ReturnObservation(date(2025, 1, 3), 0.015),
        ReturnObservation(date(2025, 1, 4), 0.020),
    )

    aligned = align_return_observations(
        asset,
        benchmark,
    )

    assert tuple(item.trade_date for item in aligned) == (
        date(2025, 1, 1),
        date(2025, 1, 3),
    )
    assert tuple(item.asset_return for item in aligned) == (
        0.01,
        0.03,
    )
    assert tuple(item.benchmark_return for item in aligned) == (
        0.005,
        0.015,
    )


def test_covariance_and_correlation_remain_available_below_beta_minimum() -> None:
    asset = observations((0.01, 0.02, 0.03))
    benchmark = (
        ReturnObservation(date(2025, 1, 1), 0.005),
        ReturnObservation(date(2025, 1, 3), 0.015),
        ReturnObservation(date(2025, 1, 4), 0.020),
    )

    covariance = sample_covariance(
        asset,
        benchmark,
    )
    beta_result = beta(
        asset,
        benchmark,
    )
    correlation_result = pearson_correlation(
        asset,
        benchmark,
    )

    assert covariance == pytest.approx(0.0001)

    assert beta_result.value is None
    assert beta_result.observations == 2
    assert beta_result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS

    assert correlation_result.value == pytest.approx(1.0)
    assert correlation_result.observations == 2


def test_disjoint_dates_produce_no_aligned_observations() -> None:
    asset = observations((0.01, 0.02))
    benchmark = observations(
        (0.01, 0.02),
        start=date(2025, 2, 1),
    )

    aligned = align_return_observations(
        asset,
        benchmark,
    )

    assert aligned == ()

    beta_result = beta(
        asset,
        benchmark,
    )
    correlation_result = pearson_correlation(
        asset,
        benchmark,
    )

    assert beta_result.value is None
    assert beta_result.observations == 0
    assert beta_result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS

    assert correlation_result.value is None
    assert correlation_result.observations == 0
    assert correlation_result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS


def test_alignment_rejects_duplicate_or_unsorted_dates() -> None:
    duplicate = (
        ReturnObservation(date(2025, 1, 1), 0.01),
        ReturnObservation(date(2025, 1, 1), 0.02),
    )
    ascending = observations((0.01, 0.02))

    with pytest.raises(
        ReturnAlignmentError,
        match="duplicate",
    ):
        align_return_observations(
            duplicate,
            ascending,
        )

    unsorted = (
        ReturnObservation(date(2025, 1, 2), 0.01),
        ReturnObservation(date(2025, 1, 1), 0.02),
    )

    with pytest.raises(
        ReturnAlignmentError,
        match="strictly ascending",
    ):
        align_return_observations(
            unsorted,
            ascending,
        )


def test_sample_covariance_uses_ddof_one() -> None:
    asset = observations((1.0, 2.0, 3.0))
    benchmark = observations((2.0, 4.0, 6.0))

    assert sample_covariance(
        asset,
        benchmark,
    ) == pytest.approx(2.0)


def test_sample_covariance_requires_two_pairs() -> None:
    asset = observations((0.01,))
    benchmark = observations((0.02,))

    with pytest.raises(
        ValueError,
        match="at least two",
    ):
        sample_covariance(
            asset,
            benchmark,
        )


def test_beta_is_undefined_with_59_aligned_observations() -> None:
    asset, benchmark = linear_beta_observations(MIN_BETA_OBS - 1)

    result = beta(
        asset,
        benchmark,
    )

    assert result.value is None
    assert result.observations == 59
    assert result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS
    assert "60" in result.warnings[0].message


def test_beta_is_defined_at_60_aligned_observations() -> None:
    asset, benchmark = linear_beta_observations(MIN_BETA_OBS)

    result = beta(
        asset,
        benchmark,
    )

    assert MIN_BETA_OBS == 60
    assert result.value == pytest.approx(2.0)
    assert result.observations == 60
    assert result.warnings == ()


def test_beta_minimum_is_applied_after_date_intersection() -> None:
    asset, _ = linear_beta_observations(MIN_BETA_OBS)
    _, benchmark = linear_beta_observations(MIN_BETA_OBS)

    shifted_benchmark = tuple(
        ReturnObservation(
            trade_date=observation.trade_date + timedelta(days=1),
            value=observation.value,
        )
        for observation in benchmark
    )

    result = beta(
        asset,
        shifted_benchmark,
    )

    assert result.value is None
    assert result.observations == 59
    assert result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS


def test_beta_is_undefined_when_benchmark_variance_is_zero() -> None:
    asset = observations(tuple((index + 1) / 1000.0 for index in range(MIN_BETA_OBS)))
    benchmark = observations(tuple(0.01 for _ in range(MIN_BETA_OBS)))

    result = beta(
        asset,
        benchmark,
    )

    assert result.value is None
    assert result.observations == MIN_BETA_OBS
    assert result.warnings[0].code is RelationshipWarningCode.ZERO_BENCHMARK_VARIANCE


def test_correlation_matches_positive_and_negative_linear_fixtures() -> None:
    benchmark = observations((0.01, 0.02, 0.03))

    positive = pearson_correlation(
        observations((0.02, 0.04, 0.06)),
        benchmark,
    )
    negative = pearson_correlation(
        observations((-0.02, -0.04, -0.06)),
        benchmark,
    )

    assert positive.value == pytest.approx(1.0)
    assert negative.value == pytest.approx(-1.0)


def test_correlation_is_undefined_when_asset_variance_is_zero() -> None:
    asset = observations((0.01, 0.01, 0.01))
    benchmark = observations((0.01, 0.02, 0.03))

    result = pearson_correlation(
        asset,
        benchmark,
    )

    assert result.value is None
    assert result.warnings[0].code is RelationshipWarningCode.ZERO_ASSET_VARIANCE


def test_correlation_is_undefined_when_benchmark_variance_is_zero() -> None:
    asset = observations((0.01, 0.02, 0.03))
    benchmark = observations((0.01, 0.01, 0.01))

    result = pearson_correlation(
        asset,
        benchmark,
    )

    assert result.value is None
    assert result.warnings[0].code is RelationshipWarningCode.ZERO_BENCHMARK_VARIANCE


def test_beta_and_correlation_are_undefined_for_one_pair() -> None:
    asset = observations((0.01,))
    benchmark = observations((0.02,))

    beta_result = beta(
        asset,
        benchmark,
    )
    correlation_result = pearson_correlation(
        asset,
        benchmark,
    )

    assert beta_result.value is None
    assert beta_result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS
    assert correlation_result.value is None
    assert correlation_result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS


def test_nonfinite_return_observations_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="finite",
    ):
        ReturnObservation(
            trade_date=date(2025, 1, 1),
            value=float("nan"),
        )
