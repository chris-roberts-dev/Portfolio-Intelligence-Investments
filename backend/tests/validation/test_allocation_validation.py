"""Independent validation fixtures for portfolio allocation mathematics."""

from uuid import UUID

import pytest

from portfolio_engine.portfolio.allocation import (
    derive_portfolio_allocation,
)
from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    value_portfolio,
)

ASSET_A = UUID("00000000-0000-0000-0000-000000000001")
ASSET_B = UUID("00000000-0000-0000-0000-000000000002")


def test_known_allocation_fixture_matches_manual_market_value_ratios() -> None:
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

    expected_total = 350.0
    expected_security_weights = (
        125.0 / expected_total,
        200.0 / expected_total,
    )
    expected_cash_weight = 25.0 / expected_total

    assert result.total_market_value == expected_total
    assert result.security_weights == pytest.approx(expected_security_weights)
    assert result.cash_weight == pytest.approx(expected_cash_weight)
    assert result.weight_sum == pytest.approx(1.0)
