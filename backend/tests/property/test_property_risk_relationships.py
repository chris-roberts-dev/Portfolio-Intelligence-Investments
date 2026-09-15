"""Property tests for covariance, beta, and Pearson correlation."""

from datetime import date, timedelta

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from portfolio_engine.config import MIN_BETA_OBS
from portfolio_engine.risk.relationships import (
    RelationshipWarningCode,
    ReturnObservation,
    align_return_observations,
    beta,
    pearson_correlation,
    sample_covariance,
)

INTEGER_VALUE = st.integers(
    min_value=-1000,
    max_value=1000,
)

PAIRED_SERIES = st.integers(
    min_value=2,
    max_value=30,
).flatmap(
    lambda size: st.tuples(
        st.lists(
            INTEGER_VALUE,
            min_size=size,
            max_size=size,
        ).map(tuple),
        st.lists(
            INTEGER_VALUE,
            min_size=size,
            max_size=size,
        ).map(tuple),
    )
)

BETA_PAIRED_SERIES = st.integers(
    min_value=MIN_BETA_OBS,
    max_value=80,
).flatmap(
    lambda size: st.tuples(
        st.lists(
            INTEGER_VALUE,
            min_size=size,
            max_size=size,
        ).map(tuple),
        st.lists(
            INTEGER_VALUE,
            min_size=size,
            max_size=size,
        ).map(tuple),
    )
)


def observations(
    values: tuple[int, ...],
    *,
    start: date = date(2020, 1, 1),
) -> tuple[ReturnObservation, ...]:
    return tuple(
        ReturnObservation(
            trade_date=start + timedelta(days=index),
            value=value / 10_000.0,
        )
        for index, value in enumerate(values)
    )


@given(pair=PAIRED_SERIES)
def test_sample_covariance_is_symmetric(
    pair: tuple[tuple[int, ...], tuple[int, ...]],
) -> None:
    asset_values, benchmark_values = pair
    asset = observations(asset_values)
    benchmark = observations(benchmark_values)

    assert sample_covariance(
        asset,
        benchmark,
    ) == pytest.approx(
        sample_covariance(
            benchmark,
            asset,
        ),
        rel=1e-12,
        abs=1e-12,
    )


@given(
    pair=PAIRED_SERIES,
    asset_shift=st.integers(
        min_value=-1000,
        max_value=1000,
    ),
    benchmark_shift=st.integers(
        min_value=-1000,
        max_value=1000,
    ),
)
def test_sample_covariance_is_translation_invariant(
    pair: tuple[tuple[int, ...], tuple[int, ...]],
    asset_shift: int,
    benchmark_shift: int,
) -> None:
    asset_values, benchmark_values = pair

    shifted_asset = tuple(value + asset_shift for value in asset_values)
    shifted_benchmark = tuple(value + benchmark_shift for value in benchmark_values)

    assert sample_covariance(
        observations(shifted_asset),
        observations(shifted_benchmark),
    ) == pytest.approx(
        sample_covariance(
            observations(asset_values),
            observations(benchmark_values),
        ),
        rel=1e-12,
        abs=1e-12,
    )


@given(
    pair=BETA_PAIRED_SERIES,
    scale=st.integers(
        min_value=1,
        max_value=10,
    ),
)
def test_beta_scales_with_positive_asset_scale(
    pair: tuple[tuple[int, ...], tuple[int, ...]],
    scale: int,
) -> None:
    asset_values, benchmark_values = pair
    benchmark = observations(benchmark_values)

    base = beta(
        observations(asset_values),
        benchmark,
    )
    assume(base.value is not None)

    scaled_asset = observations(tuple(value * scale for value in asset_values))
    scaled = beta(
        scaled_asset,
        benchmark,
    )

    assert scaled.value == pytest.approx(
        scale * base.value,
        rel=1e-11,
        abs=1e-12,
    )


@given(values=st.lists(INTEGER_VALUE, min_size=60, max_size=60).map(tuple))
def test_beta_minimum_is_evaluated_after_intersection(
    values: tuple[int, ...],
) -> None:
    asset = observations(
        values,
        start=date(2020, 1, 1),
    )
    benchmark = observations(
        values,
        start=date(2020, 1, 2),
    )

    result = beta(
        asset,
        benchmark,
    )

    assert result.value is None
    assert result.observations == MIN_BETA_OBS - 1
    assert result.warnings[0].code is RelationshipWarningCode.INSUFFICIENT_OBSERVATIONS


@given(
    pair=PAIRED_SERIES,
    asset_scale=st.integers(
        min_value=1,
        max_value=10,
    ),
    benchmark_scale=st.integers(
        min_value=1,
        max_value=10,
    ),
    asset_shift=st.integers(
        min_value=-1000,
        max_value=1000,
    ),
    benchmark_shift=st.integers(
        min_value=-1000,
        max_value=1000,
    ),
)
def test_correlation_is_invariant_to_positive_scale_and_translation(
    pair: tuple[tuple[int, ...], tuple[int, ...]],
    asset_scale: int,
    benchmark_scale: int,
    asset_shift: int,
    benchmark_shift: int,
) -> None:
    asset_values, benchmark_values = pair

    base = pearson_correlation(
        observations(asset_values),
        observations(benchmark_values),
    )
    assume(base.value is not None)

    transformed_asset = observations(
        tuple(value * asset_scale + asset_shift for value in asset_values)
    )
    transformed_benchmark = observations(
        tuple(value * benchmark_scale + benchmark_shift for value in benchmark_values)
    )
    transformed = pearson_correlation(
        transformed_asset,
        transformed_benchmark,
    )

    assert transformed.value == pytest.approx(
        base.value,
        rel=1e-11,
        abs=1e-12,
    )


@given(pair=PAIRED_SERIES)
def test_alignment_with_shifted_dates_equals_explicit_intersection(
    pair: tuple[tuple[int, ...], tuple[int, ...]],
) -> None:
    asset_values, benchmark_values = pair
    asset = observations(
        asset_values,
        start=date(2020, 1, 1),
    )
    benchmark = observations(
        benchmark_values,
        start=date(2020, 1, 2),
    )

    aligned = align_return_observations(
        asset,
        benchmark,
    )

    asset_by_date = {observation.trade_date: observation.value for observation in asset}
    benchmark_by_date = {observation.trade_date: observation.value for observation in benchmark}
    common_dates = tuple(
        trade_date for trade_date in asset_by_date if trade_date in benchmark_by_date
    )

    assert tuple(observation.trade_date for observation in aligned) == common_dates
    assert tuple(observation.asset_return for observation in aligned) == pytest.approx(
        tuple(asset_by_date[trade_date] for trade_date in common_dates)
    )
    assert tuple(observation.benchmark_return for observation in aligned) == pytest.approx(
        tuple(benchmark_by_date[trade_date] for trade_date in common_dates)
    )


@given(
    pair=PAIRED_SERIES,
    future_asset=st.lists(
        INTEGER_VALUE,
        max_size=10,
    ).map(tuple),
    future_benchmark=st.lists(
        INTEGER_VALUE,
        max_size=10,
    ).map(tuple),
)
def test_aligned_prefix_does_not_depend_on_future_observations(
    pair: tuple[tuple[int, ...], tuple[int, ...]],
    future_asset: tuple[int, ...],
    future_benchmark: tuple[int, ...],
) -> None:
    asset_values, benchmark_values = pair

    future_length = min(
        len(future_asset),
        len(future_benchmark),
    )
    future_asset = future_asset[:future_length]
    future_benchmark = future_benchmark[:future_length]

    prefix_asset = observations(asset_values)
    prefix_benchmark = observations(benchmark_values)
    prefix_aligned = align_return_observations(
        prefix_asset,
        prefix_benchmark,
    )

    extended_asset = observations(asset_values + future_asset)
    extended_benchmark = observations(benchmark_values + future_benchmark)
    extended_aligned = align_return_observations(
        extended_asset,
        extended_benchmark,
    )

    assert extended_aligned[: len(prefix_aligned)] == prefix_aligned
