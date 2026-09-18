"""Property tests for portfolio allocation helpers."""

import math
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.portfolio.allocation import (
    derive_portfolio_allocation,
)
from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    value_portfolio,
)


def allocation_case_from_pairs(
    pairs: list[tuple[int, int]],
    cash_cents: int,
) -> tuple[
    tuple[int, ...],
    tuple[int, ...],
    int,
]:
    quantities = tuple(quantity for quantity, _price in pairs)
    prices = tuple(price for _quantity, price in pairs)
    return quantities, prices, cash_cents


ALLOCATION_CASE = st.builds(
    allocation_case_from_pairs,
    st.lists(
        st.tuples(
            st.integers(
                min_value=1,
                max_value=100_000,
            ),
            st.integers(
                min_value=1,
                max_value=100_000,
            ),
        ),
        min_size=1,
        max_size=20,
    ),
    st.integers(
        min_value=0,
        max_value=100_000,
    ),
)


def positions(
    quantities: tuple[int, ...],
    prices: tuple[int, ...],
    *,
    price_scale: float = 1.0,
) -> tuple[AssetPositionValuationInput, ...]:
    return tuple(
        AssetPositionValuationInput(
            asset_id=UUID(int=index + 1),
            quantity=quantity / 100.0,
            valuation_price=(price / 100.0 * price_scale),
        )
        for index, (quantity, price) in enumerate(
            zip(
                quantities,
                prices,
                strict=True,
            )
        )
    )


@given(case=ALLOCATION_CASE)
def test_derived_weights_sum_to_one_within_tolerance(
    case: tuple[
        tuple[int, ...],
        tuple[int, ...],
        int,
    ],
) -> None:
    quantities, prices, cash_cents = case
    allocation = derive_portfolio_allocation(
        value_portfolio(
            positions(
                quantities,
                prices,
            ),
            cash_value=cash_cents / 100.0,
        )
    )

    assert math.isclose(
        allocation.weight_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=WEIGHT_SUM_TOLERANCE,
    )
    assert allocation.weight_sum == pytest.approx(
        math.fsum(
            (
                *allocation.security_weights,
                allocation.cash_weight,
            )
        ),
        rel=1e-12,
        abs=1e-12,
    )


@given(case=ALLOCATION_CASE)
def test_joint_position_permutation_preserves_asset_weight_mapping(
    case: tuple[
        tuple[int, ...],
        tuple[int, ...],
        int,
    ],
) -> None:
    quantities, prices, cash_cents = case
    portfolio_positions = positions(
        quantities,
        prices,
    )
    cash_value = cash_cents / 100.0

    original = derive_portfolio_allocation(
        value_portfolio(
            portfolio_positions,
            cash_value=cash_value,
        )
    )
    reversed_result = derive_portfolio_allocation(
        value_portfolio(
            tuple(reversed(portfolio_positions)),
            cash_value=cash_value,
        )
    )

    original_by_asset = {position.asset_id: position.weight for position in original.positions}
    reversed_by_asset = {
        position.asset_id: position.weight for position in reversed_result.positions
    }

    assert reversed_by_asset.keys() == original_by_asset.keys()

    for asset_id, weight in original_by_asset.items():
        assert reversed_by_asset[asset_id] == pytest.approx(
            weight,
            rel=1e-12,
            abs=1e-12,
        )

    assert reversed_result.cash_weight == pytest.approx(
        original.cash_weight,
        rel=1e-12,
        abs=1e-12,
    )


@given(
    case=ALLOCATION_CASE,
    scale=st.integers(
        min_value=1,
        max_value=20,
    ),
)
def test_proportional_valuation_scaling_preserves_allocation_weights(
    case: tuple[
        tuple[int, ...],
        tuple[int, ...],
        int,
    ],
    scale: int,
) -> None:
    quantities, prices, cash_cents = case

    original = derive_portfolio_allocation(
        value_portfolio(
            positions(
                quantities,
                prices,
            ),
            cash_value=cash_cents / 100.0,
        )
    )
    scaled = derive_portfolio_allocation(
        value_portfolio(
            positions(
                quantities,
                prices,
                price_scale=float(scale),
            ),
            cash_value=(cash_cents / 100.0 * scale),
        )
    )

    assert scaled.security_weights == pytest.approx(
        original.security_weights,
        rel=1e-11,
        abs=1e-12,
    )
    assert scaled.cash_weight == pytest.approx(
        original.cash_weight,
        rel=1e-11,
        abs=1e-12,
    )
