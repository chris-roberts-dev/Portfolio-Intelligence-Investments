"""Framework-independent contracts for canonical portfolio optimization.

Development guide references: Sections 12, 17.1, and 19.5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from portfolio_engine.config import DEFAULT_RISK_FREE_RATE

OPTIMIZATION_METHOD_VERSION = "1.0"


class OptimizationMethod(StrEnum):
    """Canonical Phase 5 optimization methods."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    MINIMUM_VARIANCE = "MINIMUM_VARIANCE"
    MAXIMUM_SHARPE = "MAXIMUM_SHARPE"
    EFFICIENT_FRONTIER = "EFFICIENT_FRONTIER"


class OptimizationErrorCode(StrEnum):
    """Stable engine failure categories exposed by the application layer."""

    INVALID_INPUT = "INVALID_INPUT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INFEASIBLE_CONSTRAINTS = "INFEASIBLE_CONSTRAINTS"
    SINGULAR_COVARIANCE = "SINGULAR_COVARIANCE"
    SOLVER_FAILED = "SOLVER_FAILED"
    POST_VALIDATION_FAILED = "POST_VALIDATION_FAILED"
    DEGENERATE_RETURN_RANGE = "DEGENERATE_RETURN_RANGE"


class OptimizationError(ValueError):
    """Raised when a canonical optimization cannot produce a valid result."""

    def __init__(
        self,
        code: OptimizationErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class WeightBound:
    """Long-only lower and upper bound for one risky asset weight."""

    minimum: float = 0.0
    maximum: float = 1.0

    def __post_init__(self) -> None:
        minimum = _finite(self.minimum, field_name="minimum")
        maximum = _finite(self.maximum, field_name="maximum")

        if minimum < 0.0 or maximum > 1.0 or minimum > maximum:
            raise OptimizationError(
                OptimizationErrorCode.INVALID_INPUT,
                "Weight bounds must satisfy 0 <= minimum <= maximum <= 1.",
            )


@dataclass(frozen=True, slots=True)
class HistoricalOptimizationEstimate:
    """Annualized historical estimates built from complete-case daily returns."""

    asset_keys: tuple[str, ...]
    return_dates: tuple[date, ...]
    observations: int
    expected_returns: tuple[float, ...]
    covariance: tuple[tuple[float, ...], ...]
    covariance_rank: int


@dataclass(frozen=True, slots=True)
class OptimizationProblem:
    """Validated numerical optimization inputs in canonical asset order."""

    asset_keys: tuple[str, ...]
    expected_returns: tuple[float, ...]
    covariance: tuple[tuple[float, ...], ...]
    bounds: tuple[WeightBound, ...]
    risk_free_rate_annual: float = DEFAULT_RISK_FREE_RATE


@dataclass(frozen=True, slots=True)
class OptimizedPortfolio:
    """One post-validated canonical optimized portfolio."""

    method: OptimizationMethod
    asset_keys: tuple[str, ...]
    weights: tuple[float, ...]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float | None
    target_return: float | None = None


@dataclass(frozen=True, slots=True)
class EfficientFrontier:
    """Ordered feasible efficient-frontier points."""

    asset_keys: tuple[str, ...]
    points: tuple[OptimizedPortfolio, ...]


def _finite(value: float, *, field_name: str) -> float:
    if isinstance(value, bool):
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            f"{field_name} must be a real finite number.",
        )

    number = float(value)
    if not math.isfinite(number):
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            f"{field_name} must be a real finite number.",
        )
    return number
