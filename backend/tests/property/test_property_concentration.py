"""Property tests for canonical portfolio concentration metrics."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.risk.concentration import (
    NormalizedPortfolioWeights,
    portfolio_concentration,
)

POSITIVE_INTEGER_WEIGHTS = st.lists(
    st.integers(min_value=1, max_value=10_000),
    min_size=1,
    max_size=30,
).map(tuple)


def normalized_weights(
    raw_weights: tuple[int, ...],
) -> tuple[float, ...]:
    total = math.fsum(raw_weights)
    weights = tuple(weight / total for weight in raw_weights[:-1])
    final_weight = 1.0 - math.fsum(weights)

    return (*weights, final_weight)


@given(raw_weights=POSITIVE_INTEGER_WEIGHTS)
def test_concentration_is_permutation_invariant(
    raw_weights: tuple[int, ...],
) -> None:
    weights = normalized_weights(raw_weights)
    reversed_weights = tuple(reversed(weights))

    original = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=weights,
        )
    )
    reversed_result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=reversed_weights,
        )
    )

    assert original.largest_position_weight is not None
    assert reversed_result.largest_position_weight is not None
    assert reversed_result.largest_position_weight == pytest.approx(
        original.largest_position_weight
    )
    assert reversed_result.herfindahl_hirschman_index == pytest.approx(
        original.herfindahl_hirschman_index
    )


@given(raw_weights=POSITIVE_INTEGER_WEIGHTS)
def test_hhi_stays_within_long_only_bounds(
    raw_weights: tuple[int, ...],
) -> None:
    weights = normalized_weights(raw_weights)
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=weights,
        )
    )

    assert 0.0 < result.herfindahl_hirschman_index <= 1.0 + WEIGHT_SUM_TOLERANCE
    assert result.largest_position_weight is not None
    assert 0.0 < result.largest_position_weight <= 1.0 + WEIGHT_SUM_TOLERANCE


@given(
    position_count=st.integers(min_value=1, max_value=30),
)
def test_equal_weights_have_hhi_inverse_to_position_count(
    position_count: int,
) -> None:
    weight = 1.0 / position_count
    weights = tuple(weight for _ in range(position_count - 1)) + (
        1.0 - weight * (position_count - 1),
    )
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=weights,
        )
    )

    assert result.largest_position_weight == pytest.approx(1.0 / position_count)
    assert result.herfindahl_hirschman_index == pytest.approx(1.0 / position_count)


@given(
    raw_weights=POSITIVE_INTEGER_WEIGHTS,
    scale=st.integers(min_value=2, max_value=10),
)
def test_scaled_normalized_weights_are_rejected_not_renormalized(
    raw_weights: tuple[int, ...],
    scale: int,
) -> None:
    weights = normalized_weights(raw_weights)
    scaled = tuple(weight * scale for weight in weights)

    with pytest.raises(ValueError):
        NormalizedPortfolioWeights(
            security_weights=scaled,
        )
