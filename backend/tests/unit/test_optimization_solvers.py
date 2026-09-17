"""Unit tests for deterministic canonical optimization solvers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from portfolio_engine.optimization import (
    OptimizationError,
    OptimizationErrorCode,
    WeightBound,
    build_problem,
    efficient_frontier,
    equal_weight_portfolio,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
    solvers,
)


def _problem():
    return build_problem(
        asset_keys=("A", "B"),
        expected_returns=(0.10, 0.14),
        covariance=((0.04, 0.0), (0.0, 0.09)),
    )


def test_equal_weight_is_one_over_n() -> None:
    result = equal_weight_portfolio(_problem())

    assert result.weights == pytest.approx((0.5, 0.5))
    assert sum(result.weights) == pytest.approx(1.0)


def test_two_asset_minimum_variance_matches_analytic_solution() -> None:
    result = minimum_variance_portfolio(_problem())

    expected_a = 0.09 / (0.04 + 0.09)
    expected_b = 1.0 - expected_a
    assert result.weights == pytest.approx((expected_a, expected_b), abs=1e-6)


def test_minimum_variance_not_more_volatile_than_equal_weight() -> None:
    problem = _problem()

    equal = equal_weight_portfolio(problem)
    minimum = minimum_variance_portfolio(problem)

    assert minimum.expected_volatility <= equal.expected_volatility + 1e-10


def test_maximum_sharpe_is_finite_and_respects_bounds() -> None:
    problem = build_problem(
        asset_keys=("A", "B"),
        expected_returns=(0.10, 0.14),
        covariance=((0.04, 0.01), (0.01, 0.09)),
        bounds=(WeightBound(0.20, 0.80), WeightBound(0.20, 0.80)),
        risk_free_rate_annual=0.02,
    )

    result = maximum_sharpe_portfolio(problem)

    assert sum(result.weights) == pytest.approx(1.0, abs=1e-8)
    assert all(0.20 - 1e-8 <= weight <= 0.80 + 1e-8 for weight in result.weights)
    assert result.sharpe_ratio is not None


def test_infeasible_bounds_fail_explicitly() -> None:
    with pytest.raises(OptimizationError) as exc_info:
        build_problem(
            asset_keys=("A", "B"),
            expected_returns=(0.10, 0.14),
            covariance=((0.04, 0.0), (0.0, 0.09)),
            bounds=(WeightBound(0.0, 0.40), WeightBound(0.0, 0.40)),
        )

    assert exc_info.value.code is OptimizationErrorCode.INFEASIBLE_CONSTRAINTS


def test_efficient_frontier_uses_explicit_target_returns() -> None:
    frontier = efficient_frontier(_problem(), points=7)

    assert len(frontier.points) == 7
    targets = tuple(point.target_return for point in frontier.points)
    assert all(target is not None for target in targets)
    assert tuple(sorted(targets)) == targets
    for point in frontier.points:
        assert sum(point.weights) == pytest.approx(1.0, abs=1e-8)


def test_repeated_runs_are_deterministic() -> None:
    first = maximum_sharpe_portfolio(_problem())
    second = maximum_sharpe_portfolio(_problem())

    assert second == first


def test_solver_failure_is_never_returned_as_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        solvers,
        "minimize",
        lambda *args, **kwargs: SimpleNamespace(
            success=False,
            message="forced failure",
            x=[0.5, 0.5],
        ),
    )

    with pytest.raises(OptimizationError) as exc_info:
        minimum_variance_portfolio(_problem())

    assert exc_info.value.code is OptimizationErrorCode.SOLVER_FAILED


def test_successful_solver_output_is_independently_post_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        solvers,
        "minimize",
        lambda *args, **kwargs: SimpleNamespace(
            success=True,
            message="fake success",
            x=[1.2, -0.2],
        ),
    )

    with pytest.raises(OptimizationError) as exc_info:
        minimum_variance_portfolio(_problem())

    assert exc_info.value.code is OptimizationErrorCode.POST_VALIDATION_FAILED


def test_failed_solve_with_rank_deficient_covariance_is_classified_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    problem = build_problem(
        asset_keys=("A", "B"),
        expected_returns=(0.10, 0.11),
        covariance=((0.04, 0.04), (0.04, 0.04)),
    )
    monkeypatch.setattr(
        solvers,
        "minimize",
        lambda *args, **kwargs: SimpleNamespace(
            success=False,
            message="forced singular failure",
            x=[0.5, 0.5],
        ),
    )

    with pytest.raises(OptimizationError) as exc_info:
        minimum_variance_portfolio(problem)

    assert exc_info.value.code is OptimizationErrorCode.SINGULAR_COVARIANCE
