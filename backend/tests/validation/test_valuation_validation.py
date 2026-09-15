"""Independent validation fixtures for portfolio valuation mathematics."""

from uuid import UUID

import pytest

from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    value_portfolio,
)

ASSET_A = UUID("00000000-0000-0000-0000-000000000001")
ASSET_B = UUID("00000000-0000-0000-0000-000000000002")


def test_known_portfolio_fixture_matches_manual_valuation() -> None:
    result = value_portfolio(
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

    expected_security_value = 10.0 * 12.5 + 4.0 * 50.0
    expected_total_value = expected_security_value + 25.0

    assert expected_security_value == 325.0
    assert expected_total_value == 350.0
    assert result.security_market_value == pytest.approx(expected_security_value)
    assert result.total_market_value == pytest.approx(expected_total_value)
