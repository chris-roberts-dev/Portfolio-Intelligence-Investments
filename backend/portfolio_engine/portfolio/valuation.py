"""Framework-independent portfolio valuation helpers.

This module values explicit security positions and keeps cash separate. It does
not round intermediate values, aggregate positions, or derive allocation weights.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AssetPositionValuationInput:
    """One security position valued at an explicit price."""

    asset_id: UUID
    quantity: float
    valuation_price: float

    def __post_init__(self) -> None:
        if not isinstance(self.asset_id, UUID):
            raise TypeError("asset_id must be a UUID")

        normalized_quantity = _finite_real(
            self.quantity,
            field_name="quantity",
        )
        normalized_price = _finite_real(
            self.valuation_price,
            field_name="valuation_price",
        )

        if normalized_quantity < 0.0:
            raise ValueError("quantity must not be negative")

        if normalized_price <= 0.0:
            raise ValueError("valuation_price must be positive")

        object.__setattr__(
            self,
            "quantity",
            normalized_quantity,
        )
        object.__setattr__(
            self,
            "valuation_price",
            normalized_price,
        )


@dataclass(frozen=True, slots=True)
class PositionValuationResult:
    """Unrounded valuation of one security position."""

    asset_id: UUID
    quantity: float
    valuation_price: float
    market_value: float


@dataclass(frozen=True, slots=True)
class PortfolioValuationResult:
    """Security valuations plus separately represented cash and total value."""

    positions: tuple[PositionValuationResult, ...]
    security_market_value: float
    cash_value: float
    total_market_value: float


def value_position(
    position: AssetPositionValuationInput,
) -> PositionValuationResult:
    """Return quantity times explicit valuation price without rounding."""
    if not isinstance(position, AssetPositionValuationInput):
        raise TypeError("position must be an AssetPositionValuationInput")

    market_value = position.quantity * position.valuation_price

    if not math.isfinite(market_value):
        raise ValueError("position market value must be finite")

    return PositionValuationResult(
        asset_id=position.asset_id,
        quantity=position.quantity,
        valuation_price=position.valuation_price,
        market_value=market_value,
    )


def value_portfolio(
    positions: Sequence[AssetPositionValuationInput],
    *,
    cash_value: float,
) -> PortfolioValuationResult:
    """Return security subtotal, explicit cash, and total portfolio value."""
    normalized_cash = _finite_real(
        cash_value,
        field_name="cash_value",
    )
    valued_positions = tuple(value_position(position) for position in positions)

    try:
        security_market_value = math.fsum(position.market_value for position in valued_positions)
        total_market_value = math.fsum((security_market_value, normalized_cash))
    except OverflowError as exc:
        raise ValueError("portfolio market value must be finite") from exc

    if not math.isfinite(security_market_value):
        raise ValueError("security market value must be finite")

    if not math.isfinite(total_market_value):
        raise ValueError("total portfolio market value must be finite")

    return PortfolioValuationResult(
        positions=valued_positions,
        security_market_value=security_market_value,
        cash_value=normalized_cash,
        total_market_value=total_market_value,
    )


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
