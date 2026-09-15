"""Hypothetical prior-period-weighted portfolio return calculations.

Development guide reference: Section 11.12.

Portfolio return for period t is calculated as the sum of prior-period asset
weights times same-period asset returns. Inputs must already be exactly aligned;
this module never fills, drops, renormalizes, or reorders observations.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from numbers import Real
from uuid import UUID

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE


class PortfolioReturnAlignmentError(ValueError):
    """Raised when return and weight inputs are not exactly aligned."""


class PortfolioWeightError(ValueError):
    """Raised when supplied portfolio weights are not valid normalized weights."""


@dataclass(frozen=True, slots=True)
class DatedAssetReturn:
    """One asset simple return over an explicit closed-open period."""

    asset_id: UUID
    period_start: date
    period_end: date
    simple_return: float

    def __post_init__(self) -> None:
        if self.period_start >= self.period_end:
            raise ValueError("period_start must be earlier than period_end")

        normalized_return = _finite_real(
            self.simple_return,
            field_name="simple_return",
        )

        if normalized_return < -1.0:
            raise ValueError("simple_return must be greater than or equal to -1")

        object.__setattr__(
            self,
            "simple_return",
            normalized_return,
        )


@dataclass(frozen=True, slots=True)
class PriorPeriodAssetWeight:
    """One long-only asset weight known at the start of a return period."""

    asset_id: UUID
    as_of_date: date
    weight: float

    def __post_init__(self) -> None:
        normalized_weight = _finite_real(
            self.weight,
            field_name="weight",
        )

        if normalized_weight < 0.0:
            raise ValueError("weight must not be negative")

        if normalized_weight > 1.0 + WEIGHT_SUM_TOLERANCE:
            raise ValueError("weight must not exceed one beyond the weight tolerance")

        object.__setattr__(
            self,
            "weight",
            normalized_weight,
        )


@dataclass(frozen=True, slots=True)
class HypotheticalWeightedReturnResult:
    """One hypothetical portfolio return with explicit anti-look-ahead metadata."""

    value: float
    period_start: date
    period_end: date
    weight_as_of_date: date
    asset_count: int
    weight_sum: float
    weight_sum_tolerance: float


def hypothetical_weighted_portfolio_return(
    asset_returns: Sequence[DatedAssetReturn],
    prior_period_weights: Sequence[PriorPeriodAssetWeight],
) -> HypotheticalWeightedReturnResult:
    """Calculate ``sum(w_(i,t-1) * r_(i,t))`` for one explicit period.

    Return observations must share one period. Weight observations must have the
    same asset IDs in the same order and be dated exactly at that period's start.
    This prevents same-period ending weights from entering the calculation.
    """
    returns = _validated_returns(asset_returns)
    weights = _validated_weights(prior_period_weights)

    if not returns:
        raise ValueError("at least one asset return is required")

    if len(returns) != len(weights):
        raise PortfolioReturnAlignmentError(
            "asset returns and prior-period weights must have equal lengths"
        )

    period_start = returns[0].period_start
    period_end = returns[0].period_end

    for return_observation in returns[1:]:
        if (
            return_observation.period_start != period_start
            or return_observation.period_end != period_end
        ):
            raise PortfolioReturnAlignmentError(
                "all asset returns must share the same period_start and period_end"
            )

    return_asset_ids = tuple(return_observation.asset_id for return_observation in returns)
    weight_asset_ids = tuple(weight_observation.asset_id for weight_observation in weights)

    if len(set(return_asset_ids)) != len(return_asset_ids):
        raise PortfolioReturnAlignmentError("asset returns must not contain duplicate asset IDs")

    if len(set(weight_asset_ids)) != len(weight_asset_ids):
        raise PortfolioReturnAlignmentError(
            "prior-period weights must not contain duplicate asset IDs"
        )

    if return_asset_ids != weight_asset_ids:
        raise PortfolioReturnAlignmentError(
            "asset returns and prior-period weights must contain "
            "identical asset IDs in identical order"
        )

    for weight_observation in weights:
        if weight_observation.as_of_date != period_start:
            raise PortfolioReturnAlignmentError(
                "every prior-period weight as_of_date must equal the return period_start"
            )

    weight_sum = math.fsum(weight_observation.weight for weight_observation in weights)

    if not math.isclose(
        weight_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=WEIGHT_SUM_TOLERANCE,
    ):
        raise PortfolioWeightError(
            "prior-period weights must sum to one within "
            f"WEIGHT_SUM_TOLERANCE={WEIGHT_SUM_TOLERANCE}"
        )

    value = math.fsum(
        weight_observation.weight * return_observation.simple_return
        for return_observation, weight_observation in zip(
            returns,
            weights,
            strict=True,
        )
    )

    if not math.isfinite(value):
        raise ValueError("hypothetical weighted portfolio return must be finite")

    return HypotheticalWeightedReturnResult(
        value=value,
        period_start=period_start,
        period_end=period_end,
        weight_as_of_date=period_start,
        asset_count=len(returns),
        weight_sum=weight_sum,
        weight_sum_tolerance=WEIGHT_SUM_TOLERANCE,
    )


def _validated_returns(
    observations: Sequence[DatedAssetReturn],
) -> tuple[DatedAssetReturn, ...]:
    validated = tuple(observations)

    for index, return_observation in enumerate(validated):
        if not isinstance(return_observation, DatedAssetReturn):
            raise TypeError(f"asset_returns[{index}] must be a DatedAssetReturn")

    return validated


def _validated_weights(
    observations: Sequence[PriorPeriodAssetWeight],
) -> tuple[PriorPeriodAssetWeight, ...]:
    validated = tuple(observations)

    for index, weight_observation in enumerate(validated):
        if not isinstance(
            weight_observation,
            PriorPeriodAssetWeight,
        ):
            raise TypeError(f"prior_period_weights[{index}] must be a PriorPeriodAssetWeight")

    return validated


def _finite_real(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
