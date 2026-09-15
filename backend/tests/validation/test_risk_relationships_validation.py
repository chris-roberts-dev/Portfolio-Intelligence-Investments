"""Independent validation fixtures for covariance, beta, and correlation."""

from datetime import date, timedelta

import pytest

from portfolio_engine.config import MIN_BETA_OBS
from portfolio_engine.risk.relationships import (
    RelationshipWarningCode,
    ReturnObservation,
    beta,
    pearson_correlation,
    sample_covariance,
)


def observations(
    values: tuple[float, ...],
) -> tuple[ReturnObservation, ...]:
    start = date(2025, 1, 1)

    return tuple(
        ReturnObservation(
            trade_date=start + timedelta(days=index),
            value=value,
        )
        for index, value in enumerate(values)
    )


def test_known_covariance_and_correlation_fixture_matches_independent_values() -> None:
    asset = observations((0.01, 0.02, -0.01, 0.03))
    benchmark = observations((0.005, 0.01, -0.005, 0.02))

    covariance = sample_covariance(
        asset,
        benchmark,
    )
    correlation_result = pearson_correlation(
        asset,
        benchmark,
    )

    assert covariance == pytest.approx(0.000175)
    assert correlation_result.value == pytest.approx(0.9844951849708404)


def test_beta_59_and_60_observation_boundary_matches_independent_fixture() -> None:
    benchmark_values = tuple((index + 1) / 1000.0 for index in range(MIN_BETA_OBS))
    asset_values = tuple(0.001 + 2.0 * benchmark_value for benchmark_value in benchmark_values)

    insufficient = beta(
        observations(asset_values[: MIN_BETA_OBS - 1]),
        observations(benchmark_values[: MIN_BETA_OBS - 1]),
    )
    sufficient = beta(
        observations(asset_values),
        observations(benchmark_values),
    )

    assert insufficient.value is None
    assert insufficient.observations == 59
    assert insufficient.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS

    assert sufficient.observations == 60
    assert sufficient.value == pytest.approx(2.0)
    assert sufficient.warnings == ()
