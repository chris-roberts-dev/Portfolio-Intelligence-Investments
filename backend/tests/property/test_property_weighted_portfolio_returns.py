"""Property tests for hypothetical weighted portfolio returns."""

from datetime import date
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.portfolio.weighted_returns import (
    DatedAssetReturn,
    PriorPeriodAssetWeight,
    hypothetical_weighted_portfolio_return,
)

RAW_WEIGHT = st.integers(
    min_value=1,
    max_value=10_000,
)
RETURN_BPS = st.integers(
    min_value=-9000,
    max_value=10_000,
)

PORTFOLIO_CASE = st.integers(
    min_value=1,
    max_value=20,
).flatmap(
    lambda size: st.tuples(
        st.lists(
            RAW_WEIGHT,
            min_size=size,
            max_size=size,
        ).map(tuple),
        st.lists(
            RETURN_BPS,
            min_size=size,
            max_size=size,
        ).map(tuple),
    )
)


def normalized_weights(
    raw_weights: tuple[int, ...],
) -> tuple[float, ...]:
    total = sum(raw_weights)
    leading = tuple(weight / total for weight in raw_weights[:-1])
    final = 1.0 - sum(leading)

    return (*leading, final)


def contracts(
    raw_weights: tuple[int, ...],
    return_bps: tuple[int, ...],
) -> tuple[
    tuple[DatedAssetReturn, ...],
    tuple[PriorPeriodAssetWeight, ...],
]:
    period_start = date(2025, 1, 2)
    period_end = date(2025, 1, 3)
    weights = normalized_weights(raw_weights)
    asset_ids = tuple(UUID(int=index + 1) for index in range(len(raw_weights)))
    returns = tuple(
        DatedAssetReturn(
            asset_id=asset_id,
            period_start=period_start,
            period_end=period_end,
            simple_return=basis_points / 10_000.0,
        )
        for asset_id, basis_points in zip(
            asset_ids,
            return_bps,
            strict=True,
        )
    )
    prior_weights = tuple(
        PriorPeriodAssetWeight(
            asset_id=asset_id,
            as_of_date=period_start,
            weight=weight,
        )
        for asset_id, weight in zip(
            asset_ids,
            weights,
            strict=True,
        )
    )

    return returns, prior_weights


@given(case=PORTFOLIO_CASE)
def test_weighted_return_is_invariant_to_joint_asset_permutation(
    case: tuple[tuple[int, ...], tuple[int, ...]],
) -> None:
    raw_weights, return_bps = case
    returns, weights = contracts(
        raw_weights,
        return_bps,
    )

    original = hypothetical_weighted_portfolio_return(
        returns,
        weights,
    )
    reversed_result = hypothetical_weighted_portfolio_return(
        tuple(reversed(returns)),
        tuple(reversed(weights)),
    )

    assert reversed_result.value == pytest.approx(
        original.value,
        rel=1e-12,
        abs=1e-12,
    )


@given(
    case=PORTFOLIO_CASE,
    scale_tenths=st.integers(
        min_value=1,
        max_value=10,
    ),
)
def test_weighted_return_is_linear_in_asset_returns(
    case: tuple[tuple[int, ...], tuple[int, ...]],
    scale_tenths: int,
) -> None:
    raw_weights, return_bps = case
    returns, weights = contracts(
        raw_weights,
        return_bps,
    )
    scale = scale_tenths / 10.0
    scaled_returns = tuple(
        DatedAssetReturn(
            asset_id=observation.asset_id,
            period_start=observation.period_start,
            period_end=observation.period_end,
            simple_return=observation.simple_return * scale,
        )
        for observation in returns
    )

    original = hypothetical_weighted_portfolio_return(
        returns,
        weights,
    )
    scaled = hypothetical_weighted_portfolio_return(
        scaled_returns,
        weights,
    )

    assert scaled.value == pytest.approx(
        original.value * scale,
        rel=1e-11,
        abs=1e-12,
    )


@given(case=PORTFOLIO_CASE)
def test_weighted_return_lies_within_asset_return_range(
    case: tuple[tuple[int, ...], tuple[int, ...]],
) -> None:
    raw_weights, return_bps = case
    returns, weights = contracts(
        raw_weights,
        return_bps,
    )
    result = hypothetical_weighted_portfolio_return(
        returns,
        weights,
    )
    values = tuple(observation.simple_return for observation in returns)

    assert min(values) - 1e-12 <= result.value <= max(values) + 1e-12


@given(case=PORTFOLIO_CASE)
def test_same_period_end_weights_can_never_replace_prior_period_weights(
    case: tuple[tuple[int, ...], tuple[int, ...]],
) -> None:
    raw_weights, return_bps = case
    returns, weights = contracts(
        raw_weights,
        return_bps,
    )
    ending_weights = tuple(
        PriorPeriodAssetWeight(
            asset_id=weight.asset_id,
            as_of_date=returns[0].period_end,
            weight=weight.weight,
        )
        for weight in weights
    )

    with pytest.raises(
        ValueError,
        match="as_of_date",
    ):
        hypothetical_weighted_portfolio_return(
            returns,
            ending_weights,
        )
