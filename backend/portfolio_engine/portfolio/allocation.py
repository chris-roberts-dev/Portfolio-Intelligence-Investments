"""Framework-independent portfolio allocation helpers.

Allocation weights are derived from explicit portfolio valuation results without
rounding or silent renormalization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from uuid import UUID

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.portfolio.valuation import PortfolioValuationResult


@dataclass(frozen=True, slots=True)
class SecurityAllocation:
    """One security allocation derived from an explicit position valuation."""

    asset_id: UUID
    market_value: float
    weight: float


@dataclass(frozen=True, slots=True)
class PortfolioAllocationResult:
    """Immutable security and cash allocation derived from a portfolio valuation."""

    positions: tuple[SecurityAllocation, ...]
    cash_value: float
    cash_weight: float
    total_market_value: float
    weight_sum: float
    weight_sum_tolerance: float

    @property
    def security_weights(self) -> tuple[float, ...]:
        """Return security weights in the original valuation-position order."""
        return tuple(position.weight for position in self.positions)


def derive_portfolio_allocation(
    valuation: PortfolioValuationResult,
) -> PortfolioAllocationResult:
    """Derive unrounded security and cash weights from an explicit valuation."""
    if not isinstance(valuation, PortfolioValuationResult):
        raise TypeError("valuation must be a PortfolioValuationResult")

    total_market_value = _finite_real(
        valuation.total_market_value,
        field_name="total_market_value",
    )
    cash_value = _finite_real(
        valuation.cash_value,
        field_name="cash_value",
    )

    if total_market_value <= 0.0:
        raise ValueError("total_market_value must be positive")

    if cash_value < 0.0:
        raise ValueError("cash_value must not be negative when deriving long-only allocations")

    positions: list[SecurityAllocation] = []

    for index, position in enumerate(valuation.positions):
        market_value = _finite_real(
            position.market_value,
            field_name=f"positions[{index}].market_value",
        )

        if market_value < 0.0:
            raise ValueError(f"positions[{index}].market_value must not be negative")

        weight = market_value / total_market_value

        if not math.isfinite(weight):
            raise ValueError(f"positions[{index}].weight must be finite")

        positions.append(
            SecurityAllocation(
                asset_id=position.asset_id,
                market_value=market_value,
                weight=weight,
            )
        )

    cash_weight = cash_value / total_market_value
    security_weights = tuple(position.weight for position in positions)
    weight_sum = math.fsum((*security_weights, cash_weight))

    if not math.isclose(
        weight_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=WEIGHT_SUM_TOLERANCE,
    ):
        raise ValueError(
            "derived security and cash weights must sum to one within "
            f"WEIGHT_SUM_TOLERANCE={WEIGHT_SUM_TOLERANCE}"
        )

    return PortfolioAllocationResult(
        positions=tuple(positions),
        cash_value=cash_value,
        cash_weight=cash_weight,
        total_market_value=total_market_value,
        weight_sum=weight_sum,
        weight_sum_tolerance=WEIGHT_SUM_TOLERANCE,
    )


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
