"""Independent validation fixtures for canonical optimization output."""

from __future__ import annotations

import math

import pytest

from portfolio_engine.optimization import build_problem, minimum_variance_portfolio


def test_two_asset_minimum_variance_matches_closed_form_independent_fixture() -> None:
    variance_a = 0.04
    variance_b = 0.09
    covariance_ab = 0.01
    problem = build_problem(
        asset_keys=("A", "B"),
        expected_returns=(0.08, 0.12),
        covariance=(
            (variance_a, covariance_ab),
            (covariance_ab, variance_b),
        ),
    )

    result = minimum_variance_portfolio(problem)

    expected_a = (variance_b - covariance_ab) / (variance_a + variance_b - 2.0 * covariance_ab)
    expected_b = 1.0 - expected_a
    expected_variance = (
        expected_a**2 * variance_a
        + expected_b**2 * variance_b
        + 2.0 * expected_a * expected_b * covariance_ab
    )

    assert result.weights == pytest.approx((expected_a, expected_b), abs=1e-6)
    assert result.expected_volatility == pytest.approx(math.sqrt(expected_variance), abs=1e-8)
