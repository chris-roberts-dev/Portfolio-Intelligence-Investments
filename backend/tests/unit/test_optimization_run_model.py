"""Unit-level persistence invariants for optimization-run resources."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.optimization.models import (
    OptimizationRun,
    OptimizationRunMethod,
    OptimizationRunStatus,
)
from apps.portfolios.models import Portfolio


@pytest.mark.django_db
def test_running_run_allows_empty_warnings() -> None:
    user = User.objects.create_user(email="running@example.test", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Running", base_currency="USD")
    run = OptimizationRun(
        user=user,
        portfolio=portfolio,
        status=OptimizationRunStatus.RUNNING,
        method=OptimizationRunMethod.MINIMUM_VARIANCE,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 1),
        provider="mock",
        included_asset_ids=["00000000-0000-0000-0000-000000000001"],
        parameters={"frontier_points": 25},
        warnings=[],
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    run.full_clean()


@pytest.mark.django_db
def test_successful_run_rejects_non_finite_public_json() -> None:
    user = User.objects.create_user(email="finite@example.test", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Finite", base_currency="USD")
    run = OptimizationRun(
        user=user,
        portfolio=portfolio,
        status=OptimizationRunStatus.SUCCEEDED,
        method=OptimizationRunMethod.MINIMUM_VARIANCE,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 1),
        provider="mock",
        result={"portfolio": {"expected_return": float("nan")}, "frontier": []},
        completed_at=datetime(2026, 2, 1, tzinfo=UTC),
    )

    with pytest.raises(ValidationError, match="NaN or infinity"):
        run.full_clean()


@pytest.mark.django_db
def test_failed_run_cannot_carry_success_result() -> None:
    user = User.objects.create_user(email="failed@example.test", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Failed", base_currency="USD")
    run = OptimizationRun(
        user=user,
        portfolio=portfolio,
        status=OptimizationRunStatus.FAILED,
        method=OptimizationRunMethod.MINIMUM_VARIANCE,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 2, 1),
        provider="mock",
        result={"portfolio": {}, "frontier": []},
        failure_code="SOLVER_FAILED",
        failure_message="forced",
        completed_at=datetime(2026, 2, 1, tzinfo=UTC),
    )

    with pytest.raises(ValidationError, match="Failed optimization runs cannot"):
        run.full_clean()
