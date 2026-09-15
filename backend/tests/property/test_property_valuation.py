"""Property tests for framework-independent portfolio valuation helpers."""

import math
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    value_portfolio,
)

VALUATION_CASE = st.integers(
    min_value=1,
    max_value=20,
).flatmap(
    lambda size: st.tuples(
        st.lists(
            st.integers(min_value=0, max_value=100_000),
            min_size=size,
            max_size=size,
        ).map(tuple),
        st.lists(
            st.integers(min_value=1, max_value=100_000),
            min_size=size,
            max_size=size,
        ).map(tuple),
        st.integers(
            min_value=-100_000,
            max_value=100_000,
        ),
        st.integers(
            min_value=0,
            max_value=size,
        ),
    )
)


def positions(
    quantities: tuple[int, ...],
    prices: tuple[int, ...],
) -> tuple[AssetPositionValuationInput, ...]:
    return tuple(
        AssetPositionValuationInput(
            asset_id=UUID(int=index + 1),
            quantity=quantity / 100.0,
            valuation_price=price / 100.0,
        )
        for index, (quantity, price) in enumerate(
            zip(
                quantities,
                prices,
                strict=True,
            )
        )
    )


@given(case=VALUATION_CASE)
def test_portfolio_value_is_permutation_invariant(
    case: tuple[
        tuple[int, ...],
        tuple[int, ...],
        int,
        int,
    ],
) -> None:
    quantities, prices, cash_cents, _ = case
    portfolio_positions = positions(
        quantities,
        prices,
    )
    cash_value = cash_cents / 100.0

    original = value_portfolio(
        portfolio_positions,
        cash_value=cash_value,
    )
    reversed_result = value_portfolio(
        tuple(reversed(portfolio_positions)),
        cash_value=cash_value,
    )

    assert reversed_result.security_market_value == pytest.approx(
        original.security_market_value,
        rel=1e-12,
        abs=1e-12,
    )
    assert reversed_result.total_market_value == pytest.approx(
        original.total_market_value,
        rel=1e-12,
        abs=1e-12,
    )


@given(case=VALUATION_CASE)
def test_security_market_value_is_additive_across_position_partitions(
    case: tuple[
        tuple[int, ...],
        tuple[int, ...],
        int,
        int,
    ],
) -> None:
    quantities, prices, cash_cents, split_index = case
    portfolio_positions = positions(
        quantities,
        prices,
    )
    cash_value = cash_cents / 100.0

    whole = value_portfolio(
        portfolio_positions,
        cash_value=cash_value,
    )
    left = value_portfolio(
        portfolio_positions[:split_index],
        cash_value=0.0,
    )
    right = value_portfolio(
        portfolio_positions[split_index:],
        cash_value=0.0,
    )

    combined_security_value = math.fsum(
        (
            left.security_market_value,
            right.security_market_value,
        )
    )

    assert whole.security_market_value == pytest.approx(
        combined_security_value,
        rel=1e-12,
        abs=1e-12,
    )
    assert whole.total_market_value == pytest.approx(
        math.fsum(
            (
                combined_security_value,
                cash_value,
            )
        ),
        rel=1e-12,
        abs=1e-12,
    )
