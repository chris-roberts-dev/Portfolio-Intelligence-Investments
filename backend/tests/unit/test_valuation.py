"""Unit tests for framework-independent portfolio valuation helpers."""

from uuid import UUID

import pytest

from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    value_portfolio,
    value_position,
)

ASSET_A = UUID("00000000-0000-0000-0000-000000000001")
ASSET_B = UUID("00000000-0000-0000-0000-000000000002")


def test_single_position_market_value_is_quantity_times_price() -> None:
    position = AssetPositionValuationInput(
        asset_id=ASSET_A,
        quantity=10.0,
        valuation_price=12.5,
    )

    result = value_position(position)

    assert result.asset_id == ASSET_A
    assert result.quantity == 10.0
    assert result.valuation_price == 12.5
    assert result.market_value == 125.0


def test_multi_position_portfolio_preserves_cash_separately() -> None:
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

    assert len(result.positions) == 2
    assert result.security_market_value == 325.0
    assert result.cash_value == 25.0
    assert result.total_market_value == 350.0


def test_cash_only_portfolio_keeps_cash_out_of_security_positions() -> None:
    result = value_portfolio(
        (),
        cash_value=250.0,
    )

    assert result.positions == ()
    assert result.security_market_value == 0.0
    assert result.cash_value == 250.0
    assert result.total_market_value == 250.0


def test_position_valuation_does_not_round_intermediate_value() -> None:
    position = AssetPositionValuationInput(
        asset_id=ASSET_A,
        quantity=1.25,
        valuation_price=10.123456789,
    )

    result = value_position(position)

    assert result.market_value == (position.quantity * position.valuation_price)


def test_zero_quantity_is_valid_with_positive_price() -> None:
    result = value_position(
        AssetPositionValuationInput(
            asset_id=ASSET_A,
            quantity=0.0,
            valuation_price=100.0,
        )
    )

    assert result.market_value == 0.0


def test_negative_quantity_is_rejected() -> None:
    with pytest.raises(ValueError, match="quantity"):
        AssetPositionValuationInput(
            asset_id=ASSET_A,
            quantity=-1.0,
            valuation_price=100.0,
        )


@pytest.mark.parametrize(
    "valuation_price",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
def test_nonpositive_or_nonfinite_price_is_rejected(
    valuation_price: float,
) -> None:
    with pytest.raises(ValueError):
        AssetPositionValuationInput(
            asset_id=ASSET_A,
            quantity=1.0,
            valuation_price=valuation_price,
        )


@pytest.mark.parametrize(
    "quantity",
    [
        float("nan"),
        float("inf"),
    ],
)
def test_nonfinite_quantity_is_rejected(
    quantity: float,
) -> None:
    with pytest.raises(ValueError, match="finite"):
        AssetPositionValuationInput(
            asset_id=ASSET_A,
            quantity=quantity,
            valuation_price=100.0,
        )


def test_nonfinite_cash_is_rejected() -> None:
    with pytest.raises(ValueError, match="cash_value"):
        value_portfolio(
            (),
            cash_value=float("nan"),
        )
