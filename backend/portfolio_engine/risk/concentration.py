"""Canonical long-only portfolio concentration calculations.

Development guide references: Sections 11.13, 19.4, and 27.

The default portfolio-security HHI excludes cash. Security and cash weights are
accepted only when they are already normalized within the configured tolerance;
this module never silently renormalizes supplied weights.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE


@dataclass(frozen=True, slots=True)
class NormalizedPortfolioWeights:
    """Validated long-only portfolio weights with cash represented separately."""

    security_weights: tuple[float, ...]
    cash_weight: float = 0.0

    def __post_init__(self) -> None:
        normalized_security_weights = tuple(
            _validated_weight(
                weight,
                field_name=f"security_weights[{index}]",
            )
            for index, weight in enumerate(self.security_weights)
        )
        normalized_cash_weight = _validated_weight(
            self.cash_weight,
            field_name="cash_weight",
        )
        total_weight = math.fsum((*normalized_security_weights, normalized_cash_weight))

        if not math.isclose(
            total_weight,
            1.0,
            rel_tol=0.0,
            abs_tol=WEIGHT_SUM_TOLERANCE,
        ):
            raise ValueError(
                "security and cash weights must sum to one within "
                f"WEIGHT_SUM_TOLERANCE={WEIGHT_SUM_TOLERANCE}"
            )

        object.__setattr__(
            self,
            "security_weights",
            normalized_security_weights,
        )
        object.__setattr__(
            self,
            "cash_weight",
            normalized_cash_weight,
        )


@dataclass(frozen=True, slots=True)
class ConcentrationResult:
    """Canonical portfolio-security concentration metrics and assumptions."""

    largest_position_weight: float | None
    herfindahl_hirschman_index: float
    security_position_count: int
    cash_weight: float
    largest_position_includes_cash: bool
    hhi_includes_cash: bool
    long_only: bool
    weight_sum_tolerance: float


def portfolio_concentration(
    weights: NormalizedPortfolioWeights,
) -> ConcentrationResult:
    """Return largest security weight and security-only HHI.

    Cash is intentionally excluded from the HHI in accordance with the default
    portfolio-security HHI convention. Security weights are not renormalized
    after cash is excluded.
    """
    security_weights = weights.security_weights
    largest_position = max(security_weights) if security_weights else None
    hhi = math.fsum(weight * weight for weight in security_weights)

    if not math.isfinite(hhi):
        raise ValueError("Herfindahl-Hirschman index must be finite")

    return ConcentrationResult(
        largest_position_weight=largest_position,
        herfindahl_hirschman_index=hhi,
        security_position_count=len(security_weights),
        cash_weight=weights.cash_weight,
        largest_position_includes_cash=False,
        hhi_includes_cash=False,
        long_only=True,
        weight_sum_tolerance=WEIGHT_SUM_TOLERANCE,
    )


def _validated_weight(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    weight = float(value)

    if not math.isfinite(weight):
        raise ValueError(f"{field_name} must be finite")

    if weight < 0.0:
        raise ValueError(f"{field_name} must not be negative")

    if weight > 1.0 + WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"{field_name} must not exceed one beyond the weight tolerance")

    return weight
