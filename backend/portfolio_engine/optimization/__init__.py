"""Canonical framework-independent Phase 5 optimization engine."""

from portfolio_engine.optimization.contracts import (
    EfficientFrontier,
    HistoricalOptimizationEstimate,
    OptimizationError,
    OptimizationErrorCode,
    OptimizationMethod,
    OptimizationProblem,
    OptimizedPortfolio,
    WeightBound,
)
from portfolio_engine.optimization.estimators import estimate_historical_inputs
from portfolio_engine.optimization.solvers import (
    build_problem,
    efficient_frontier,
    equal_weight_portfolio,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
)

__all__ = [
    "EfficientFrontier",
    "HistoricalOptimizationEstimate",
    "OptimizationError",
    "OptimizationErrorCode",
    "OptimizationMethod",
    "OptimizationProblem",
    "OptimizedPortfolio",
    "WeightBound",
    "build_problem",
    "efficient_frontier",
    "equal_weight_portfolio",
    "estimate_historical_inputs",
    "maximum_sharpe_portfolio",
    "minimum_variance_portfolio",
]
