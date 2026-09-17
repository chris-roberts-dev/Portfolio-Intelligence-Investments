"""Deterministic SciPy solvers for canonical Phase 5 portfolio optimization.

Development guide references: Sections 12.4 through 12.9 and 19.5.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import NoReturn

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import LinearConstraint, linprog, minimize

from portfolio_engine.config import (
    OPTIMIZATION_MAX_FRONTIER_POINTS,
    OPTIMIZATION_MAX_SOLVER_ITERATIONS,
    OPTIMIZATION_POST_VALIDATION_TOLERANCE,
    OPTIMIZATION_SOLVER_TOLERANCE,
    OPTIMIZATION_TARGET_RETURN_TOLERANCE,
    WEIGHT_SUM_TOLERANCE,
)
from portfolio_engine.optimization.contracts import (
    EfficientFrontier,
    OptimizationError,
    OptimizationErrorCode,
    OptimizationMethod,
    OptimizationProblem,
    OptimizedPortfolio,
    WeightBound,
)

SOLVER_TOLERANCE = OPTIMIZATION_SOLVER_TOLERANCE
POST_VALIDATION_TOLERANCE = max(
    WEIGHT_SUM_TOLERANCE,
    OPTIMIZATION_POST_VALIDATION_TOLERANCE,
)
TARGET_RETURN_TOLERANCE = OPTIMIZATION_TARGET_RETURN_TOLERANCE
MAX_SOLVER_ITERATIONS = OPTIMIZATION_MAX_SOLVER_ITERATIONS

type FloatArray = NDArray[np.float64]
type Objective = Callable[[FloatArray], float]


def build_problem(
    *,
    asset_keys: Sequence[str],
    expected_returns: Sequence[float],
    covariance: Sequence[Sequence[float]],
    bounds: Sequence[WeightBound] | None = None,
    risk_free_rate_annual: float = 0.0,
) -> OptimizationProblem:
    """Validate and normalize one optimization problem."""
    keys = tuple(asset_keys)
    expected = tuple(
        _finite(
            value,
            "expected_returns",
        )
        for value in expected_returns
    )
    covariance_rows = tuple(
        tuple(
            _finite(
                value,
                "covariance",
            )
            for value in row
        )
        for row in covariance
    )

    if not keys or len(set(keys)) != len(keys):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            "asset_keys must be non-empty and unique.",
        )

    if len(expected) != len(keys):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            "expected_returns length must match assets.",
        )

    if len(covariance_rows) != len(keys) or any(len(row) != len(keys) for row in covariance_rows):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            "covariance must be an NxN matrix.",
        )

    covariance_array = np.asarray(
        covariance_rows,
        dtype=float,
    )

    if not np.allclose(
        covariance_array,
        covariance_array.T,
        rtol=0.0,
        atol=1e-10,
    ):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            "covariance must be symmetric.",
        )

    if (
        float(
            np.min(
                np.linalg.eigvalsh(
                    covariance_array,
                )
            )
        )
        < -1e-10
    ):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            "covariance must be positive semidefinite within tolerance.",
        )

    normalized_bounds = tuple(bounds) if bounds is not None else tuple(WeightBound() for _ in keys)

    if len(normalized_bounds) != len(keys):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            "bounds length must match assets.",
        )

    minimum_sum = sum(bound.minimum for bound in normalized_bounds)
    maximum_sum = sum(bound.maximum for bound in normalized_bounds)

    if (
        minimum_sum > 1.0 + POST_VALIDATION_TOLERANCE
        or maximum_sum < 1.0 - POST_VALIDATION_TOLERANCE
    ):
        _raise(
            OptimizationErrorCode.INFEASIBLE_CONSTRAINTS,
            "Weight bounds do not admit a fully invested portfolio.",
        )

    risk_free = _finite(
        risk_free_rate_annual,
        "risk_free_rate_annual",
    )

    return OptimizationProblem(
        asset_keys=keys,
        expected_returns=expected,
        covariance=covariance_rows,
        bounds=normalized_bounds,
        risk_free_rate_annual=risk_free,
    )


def equal_weight_portfolio(
    problem: OptimizationProblem,
) -> OptimizedPortfolio:
    """Return the canonical 1/N portfolio when it satisfies configured bounds."""
    weight = 1.0 / len(problem.asset_keys)
    weights = tuple(weight for _ in problem.asset_keys)

    try:
        _validate_weights(
            problem,
            weights,
        )
    except OptimizationError as exc:
        if exc.code is OptimizationErrorCode.POST_VALIDATION_FAILED:
            raise OptimizationError(
                OptimizationErrorCode.INFEASIBLE_CONSTRAINTS,
                "Equal-weight allocation violates configured weight bounds.",
            ) from exc

        raise

    return _portfolio_result(
        problem,
        weights,
        method=OptimizationMethod.EQUAL_WEIGHT,
    )


def minimum_variance_portfolio(
    problem: OptimizationProblem,
) -> OptimizedPortfolio:
    """Minimize annual portfolio variance subject to canonical constraints."""
    covariance = np.asarray(
        problem.covariance,
        dtype=float,
    )

    def objective(
        weights: FloatArray,
    ) -> float:
        return float(weights @ covariance @ weights)

    weights = _solve_slsqp(
        problem,
        objective=objective,
    )

    return _portfolio_result(
        problem,
        weights,
        method=OptimizationMethod.MINIMUM_VARIANCE,
    )


def maximum_sharpe_portfolio(
    problem: OptimizationProblem,
) -> OptimizedPortfolio:
    """Maximize canonical historical annual Sharpe subject to weight constraints."""
    expected = np.asarray(
        problem.expected_returns,
        dtype=float,
    )
    covariance = np.asarray(
        problem.covariance,
        dtype=float,
    )

    def objective(
        weights: FloatArray,
    ) -> float:
        variance = float(weights @ covariance @ weights)

        if variance <= SOLVER_TOLERANCE:
            return 1e12

        volatility = math.sqrt(variance)

        sharpe = (float(expected @ weights) - problem.risk_free_rate_annual) / volatility

        return -sharpe if math.isfinite(sharpe) else 1e12

    weights = _solve_slsqp(
        problem,
        objective=objective,
    )

    result = _portfolio_result(
        problem,
        weights,
        method=OptimizationMethod.MAXIMUM_SHARPE,
    )

    if result.sharpe_ratio is None:
        _raise(
            OptimizationErrorCode.SOLVER_FAILED,
            "Maximum-Sharpe optimization produced zero portfolio volatility.",
        )

    return result


def efficient_frontier(
    problem: OptimizationProblem,
    *,
    points: int = 25,
) -> EfficientFrontier:
    """Generate constrained minimum-variance portfolios at explicit target returns."""
    if (
        isinstance(points, bool)
        or not isinstance(points, int)
        or points < 2
        or points > OPTIMIZATION_MAX_FRONTIER_POINTS
    ):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            (f"points must be an integer between 2 and {OPTIMIZATION_MAX_FRONTIER_POINTS}."),
        )

    (
        minimum_return,
        maximum_return,
    ) = _feasible_return_range(
        problem,
    )

    if maximum_return - minimum_return <= TARGET_RETURN_TOLERANCE:
        _raise(
            OptimizationErrorCode.DEGENERATE_RETURN_RANGE,
            ("Feasible expected-return range is too narrow for an efficient frontier."),
        )

    targets = np.linspace(
        minimum_return,
        maximum_return,
        num=points,
        dtype=float,
    )

    frontier_points = tuple(
        _minimum_variance_for_target(
            problem,
            target_return=float(target),
        )
        for target in targets
    )

    return EfficientFrontier(
        asset_keys=problem.asset_keys,
        points=frontier_points,
    )


def _minimum_variance_for_target(
    problem: OptimizationProblem,
    *,
    target_return: float,
) -> OptimizedPortfolio:
    covariance = np.asarray(
        problem.covariance,
        dtype=float,
    )

    def objective(
        weights: FloatArray,
    ) -> float:
        return float(weights @ covariance @ weights)

    weights = _solve_slsqp(
        problem,
        objective=objective,
        target_return=target_return,
    )

    return _portfolio_result(
        problem,
        weights,
        method=OptimizationMethod.EFFICIENT_FRONTIER,
        target_return=target_return,
    )


def _solve_slsqp(
    problem: OptimizationProblem,
    *,
    objective: Objective,
    target_return: float | None = None,
) -> tuple[float, ...]:
    expected = np.asarray(
        problem.expected_returns,
        dtype=np.float64,
    )
    covariance = np.asarray(
        problem.covariance,
        dtype=np.float64,
    )

    scipy_bounds = tuple(
        (
            bound.minimum,
            bound.maximum,
        )
        for bound in problem.bounds
    )

    constraint_rows: list[FloatArray] = [
        np.ones(
            len(problem.asset_keys),
            dtype=np.float64,
        ),
    ]
    constraint_values: list[float] = [
        1.0,
    ]

    if target_return is not None:
        constraint_rows.append(expected)
        constraint_values.append(
            target_return,
        )

        initial = _linear_feasible_weights(
            problem,
            target_return=target_return,
        )
    else:
        initial = _deterministic_feasible_weights(
            problem.bounds,
        )

    constraint_matrix = np.vstack(
        constraint_rows,
    )
    constraint_targets = np.asarray(
        constraint_values,
        dtype=np.float64,
    )

    linear_constraint = LinearConstraint(
        constraint_matrix,
        lb=constraint_targets,
        ub=constraint_targets,
    )

    result = minimize(
        objective,
        x0=list(initial),
        method="SLSQP",
        bounds=scipy_bounds,
        constraints=linear_constraint,
        options={
            "ftol": SOLVER_TOLERANCE,
            "maxiter": MAX_SOLVER_ITERATIONS,
            "disp": False,
        },
    )

    if not bool(result.success):
        rank = int(
            np.linalg.matrix_rank(
                covariance,
                tol=1e-12,
            )
        )

        code = (
            OptimizationErrorCode.SINGULAR_COVARIANCE
            if rank < len(problem.asset_keys)
            else OptimizationErrorCode.SOLVER_FAILED
        )

        _raise(
            code,
            f"SciPy SLSQP failed: {result.message}.",
        )

    if result.x is None:
        _raise(
            OptimizationErrorCode.SOLVER_FAILED,
            "SciPy SLSQP reported success without solution weights.",
        )

    weights = tuple(float(value) for value in result.x)

    _validate_weights(
        problem,
        weights,
        target_return=target_return,
    )

    return weights


def _feasible_return_range(
    problem: OptimizationProblem,
) -> tuple[float, float]:
    expected = np.asarray(
        problem.expected_returns,
        dtype=np.float64,
    )
    bounds = tuple(
        (
            bound.minimum,
            bound.maximum,
        )
        for bound in problem.bounds
    )
    a_eq = np.ones(
        (
            1,
            len(problem.asset_keys),
        ),
        dtype=np.float64,
    )
    b_eq = np.array(
        [1.0],
        dtype=np.float64,
    )

    minimum = linprog(
        c=expected,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    maximum = linprog(
        c=-expected,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    minimum_fun = minimum.fun
    maximum_fun = maximum.fun

    if not minimum.success or not maximum.success or minimum_fun is None or maximum_fun is None:
        _raise(
            OptimizationErrorCode.INFEASIBLE_CONSTRAINTS,
            ("Weight constraints do not admit a feasible expected-return range."),
        )

    return (
        float(minimum_fun),
        -float(maximum_fun),
    )


def _linear_feasible_weights(
    problem: OptimizationProblem,
    *,
    target_return: float,
) -> tuple[float, ...]:
    expected = np.asarray(
        problem.expected_returns,
        dtype=np.float64,
    )

    result = linprog(
        c=np.zeros(
            len(problem.asset_keys),
            dtype=np.float64,
        ),
        A_eq=np.vstack(
            [
                np.ones(
                    len(problem.asset_keys),
                    dtype=np.float64,
                ),
                expected,
            ]
        ),
        b_eq=np.array(
            [
                1.0,
                target_return,
            ],
            dtype=np.float64,
        ),
        bounds=tuple(
            (
                bound.minimum,
                bound.maximum,
            )
            for bound in problem.bounds
        ),
        method="highs",
    )

    solution = result.x

    if not result.success or solution is None:
        _raise(
            OptimizationErrorCode.INFEASIBLE_CONSTRAINTS,
            (f"Target return {target_return:.12g} is infeasible under configured bounds."),
        )

    return tuple(float(value) for value in solution)


def _deterministic_feasible_weights(
    bounds: Sequence[WeightBound],
) -> tuple[float, ...]:
    weights = [bound.minimum for bound in bounds]
    remainder = 1.0 - sum(weights)
    capacities = [bound.maximum - bound.minimum for bound in bounds]

    while remainder > POST_VALIDATION_TOLERANCE:
        active = [index for index, capacity in enumerate(capacities) if capacity > 0.0]

        if not active:
            _raise(
                OptimizationErrorCode.INFEASIBLE_CONSTRAINTS,
                ("Weight bounds do not admit a fully invested portfolio."),
            )

        share = remainder / len(active)
        allocated = 0.0

        for index in active:
            increment = min(
                share,
                capacities[index],
            )
            weights[index] += increment
            capacities[index] -= increment
            allocated += increment

        if allocated <= 0.0:
            _raise(
                OptimizationErrorCode.INFEASIBLE_CONSTRAINTS,
                ("Weight bounds do not admit a fully invested portfolio."),
            )

        remainder -= allocated

    if abs(sum(weights) - 1.0) <= POST_VALIDATION_TOLERANCE:
        weights[-1] += 1.0 - sum(weights)

    return tuple(weights)


def _portfolio_result(
    problem: OptimizationProblem,
    weights: Sequence[float],
    *,
    method: OptimizationMethod,
    target_return: float | None = None,
) -> OptimizedPortfolio:
    normalized = tuple(float(value) for value in weights)

    _validate_weights(
        problem,
        normalized,
        target_return=target_return,
    )

    weight_array = np.asarray(
        normalized,
        dtype=np.float64,
    )
    expected = np.asarray(
        problem.expected_returns,
        dtype=np.float64,
    )
    covariance = np.asarray(
        problem.covariance,
        dtype=np.float64,
    )

    expected_return = float(expected @ weight_array)
    variance = float(weight_array @ covariance @ weight_array)

    if variance < -POST_VALIDATION_TOLERANCE:
        _raise(
            OptimizationErrorCode.POST_VALIDATION_FAILED,
            ("Optimized portfolio variance is negative beyond tolerance."),
        )

    variance = max(
        0.0,
        variance,
    )
    volatility = math.sqrt(variance)
    sharpe = None

    if volatility > SOLVER_TOLERANCE:
        sharpe = (expected_return - problem.risk_free_rate_annual) / volatility

        if not math.isfinite(sharpe):
            _raise(
                OptimizationErrorCode.POST_VALIDATION_FAILED,
                ("Optimized portfolio Sharpe ratio must be finite when defined."),
            )

    return OptimizedPortfolio(
        method=method,
        asset_keys=problem.asset_keys,
        weights=normalized,
        expected_return=expected_return,
        expected_volatility=volatility,
        sharpe_ratio=sharpe,
        target_return=target_return,
    )


def _validate_weights(
    problem: OptimizationProblem,
    weights: Sequence[float],
    *,
    target_return: float | None = None,
) -> None:
    if len(weights) != len(problem.asset_keys):
        _raise(
            OptimizationErrorCode.POST_VALIDATION_FAILED,
            ("Solver weight count does not match asset count."),
        )

    normalized = tuple(
        _finite(
            value,
            "weight",
        )
        for value in weights
    )

    if abs(sum(normalized) - 1.0) > POST_VALIDATION_TOLERANCE:
        _raise(
            OptimizationErrorCode.POST_VALIDATION_FAILED,
            ("Optimized weights do not sum to one within tolerance."),
        )

    for (
        index,
        (
            weight,
            bound,
        ),
    ) in enumerate(
        zip(
            normalized,
            problem.bounds,
            strict=True,
        )
    ):
        if (
            weight < bound.minimum - POST_VALIDATION_TOLERANCE
            or weight > bound.maximum + POST_VALIDATION_TOLERANCE
        ):
            _raise(
                OptimizationErrorCode.POST_VALIDATION_FAILED,
                (f"Optimized weight {index} violates its configured bounds."),
            )

    if target_return is not None:
        actual = float(
            np.asarray(
                problem.expected_returns,
                dtype=np.float64,
            )
            @ np.asarray(
                normalized,
                dtype=np.float64,
            )
        )

        if abs(actual - target_return) > TARGET_RETURN_TOLERANCE:
            _raise(
                OptimizationErrorCode.POST_VALIDATION_FAILED,
                ("Optimized weights do not satisfy target return within tolerance."),
            )


def _finite(
    value: float,
    field_name: str,
) -> float:
    if isinstance(
        value,
        bool,
    ):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            f"{field_name} must be finite.",
        )

    number = float(value)

    if not math.isfinite(number):
        _raise(
            OptimizationErrorCode.INVALID_INPUT,
            f"{field_name} must be finite.",
        )

    return number


def _raise(
    code: OptimizationErrorCode,
    message: str,
) -> NoReturn:
    raise OptimizationError(
        code,
        message,
    )
