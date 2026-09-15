"""Unit tests for framework-independent portfolio allocation helpers."""

from uuid import UUID

import pytest

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.portfolio.allocation import (
    derive_portfolio_allocation,
)
from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    value_portfolio,
)
from portfolio_engine.risk.concentration import (
    NormalizedPortfolioWeights,
    portfolio_concentration,
)

ASSET_A = UUID("00000000-0000-0000-0000-000000000001")
ASSET_B = UUID("00000000-0000-0000-0000-000000000002")


def test_single_security_allocation_is_one() -> None:
    valuation = value_portfolio(
        (
            AssetPositionValuationInput(
                asset_id=ASSET_A,
                quantity=10.0,
                valuation_price=10.0,
            ),
        ),
        cash_value=0.0,
    )

    result = derive_portfolio_allocation(valuation)

    assert result.security_weights == (1.0,)
    assert result.cash_weight == 0.0
    assert result.weight_sum == pytest.approx(1.0)


def test_multi_security_allocation_preserves_order_and_cash() -> None:
    valuation = value_portfolio(
        (
            AssetPositionValuationInput(
                asset_id=ASSET_A,
                quantity=10.0,
                valuation_price=12.5,
            ),
            AssetPositionValuationInput(
                asset_id=ASSET_B,
                quantity=4.0,
                valuation_price=50.0,
            ),
        ),
        cash_value=25.0,
    )

    result = derive_portfolio_allocation(valuation)

    assert tuple(item.asset_id for item in result.positions) == (
        ASSET_A,
        ASSET_B,
    )
    assert result.security_weights == pytest.approx(
        (
            125.0 / 350.0,
            200.0 / 350.0,
        )
    )
    assert result.cash_weight == pytest.approx(25.0 / 350.0)
    assert result.weight_sum == pytest.approx(1.0)
    assert result.weight_sum_tolerance == WEIGHT_SUM_TOLERANCE


def test_cash_only_positive_portfolio_has_cash_weight_one() -> None:
    result = derive_portfolio_allocation(
        value_portfolio(
            (),
            cash_value=250.0,
        )
    )

    assert result.positions == ()
    assert result.security_weights == ()
    assert result.cash_weight == 1.0
    assert result.weight_sum == 1.0


def test_nonpositive_total_market_value_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="total_market_value",
    ):
        derive_portfolio_allocation(
            value_portfolio(
                (),
                cash_value=0.0,
            )
        )


def test_negative_cash_is_rejected_for_long_only_allocation() -> None:
    valuation = value_portfolio(
        (
            AssetPositionValuationInput(
                asset_id=ASSET_A,
                quantity=2.0,
                valuation_price=100.0,
            ),
        ),
        cash_value=-50.0,
    )

    with pytest.raises(
        ValueError,
        match="cash_value",
    ):
        derive_portfolio_allocation(valuation)


def test_allocation_is_structurally_compatible_with_concentration_weights() -> None:
    valuation = value_portfolio(
        (
            AssetPositionValuationInput(
                asset_id=ASSET_A,
                quantity=10.0,
                valuation_price=12.5,
            ),
            AssetPositionValuationInput(
                asset_id=ASSET_B,
                quantity=4.0,
                valuation_price=50.0,
            ),
        ),
        cash_value=25.0,
    )
    allocation = derive_portfolio_allocation(valuation)

    concentration = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=allocation.security_weights,
            cash_weight=allocation.cash_weight,
        )
    )

    assert concentration.cash_weight == pytest.approx(allocation.cash_weight)
    assert concentration.largest_position_weight == pytest.approx(200.0 / 350.0)
