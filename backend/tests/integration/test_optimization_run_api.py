"""Integration coverage for persisted owner-scoped optimization runs."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.optimization.models import OptimizationRun, OptimizationRunStatus
from apps.portfolios.management.commands.seed_sample_portfolio import (
    SAMPLE_AAPL_ID,
    SAMPLE_MSFT_ID,
    SAMPLE_PORTFOLIO_ID,
    SAMPLE_USER_EMAIL,
)


@pytest.mark.django_db
@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="csv",
    MARKET_DATA_ALLOWED_PROVIDERS=("csv",),
)
def test_minimum_variance_run_persists_result_and_provenance() -> None:
    call_command("seed_sample_portfolio", reset=True, verbosity=0)
    user = User.objects.get(email=SAMPLE_USER_EMAIL)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse("api-v1-optimization-run-list"),
        {
            "portfolio_id": str(SAMPLE_PORTFOLIO_ID),
            "method": "MINIMUM_VARIANCE",
            "start": "2026-03-16",
            "end": "2026-09-16",
            "asset_ids": [str(SAMPLE_AAPL_ID), str(SAMPLE_MSFT_ID)],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "SUCCEEDED"
    assert response.data["result"]["portfolio"] is not None
    weights = response.data["result"]["portfolio"]["weights"]
    assert sum(item["weight"] for item in weights) == pytest.approx(1.0, abs=1e-8)
    assert response.data["provenance"]["provider"] == "csv"
    assert response.data["provenance"]["price_field"] == "adjusted_close"
    assert response.data["provenance"]["annualization_factor"] == 252
    assert response.data["provenance"]["data_fingerprint"]
    assert response.data["parameters"]["observations"] > 1

    run = OptimizationRun.objects.get(id=response.data["id"])
    assert run.status == OptimizationRunStatus.SUCCEEDED
    assert run.started_at is not None
    assert run.completed_at is not None
    assert run.failure_code == ""


@pytest.mark.django_db
@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="csv",
    MARKET_DATA_ALLOWED_PROVIDERS=("csv",),
)
def test_infeasible_constraints_persist_failed_auditable_run() -> None:
    call_command("seed_sample_portfolio", reset=True, verbosity=0)
    user = User.objects.get(email=SAMPLE_USER_EMAIL)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse("api-v1-optimization-run-list"),
        {
            "portfolio_id": str(SAMPLE_PORTFOLIO_ID),
            "method": "MINIMUM_VARIANCE",
            "start": "2026-03-16",
            "end": "2026-09-16",
            "asset_ids": [str(SAMPLE_AAPL_ID), str(SAMPLE_MSFT_ID)],
            "bounds": [
                {
                    "asset_id": str(SAMPLE_AAPL_ID),
                    "minimum": 0.0,
                    "maximum": 0.4,
                },
                {
                    "asset_id": str(SAMPLE_MSFT_ID),
                    "minimum": 0.0,
                    "maximum": 0.4,
                },
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "FAILED"
    assert response.data["result"] is None
    assert response.data["failure_code"] == "OPTIMIZATION_INFEASIBLE"
    run = OptimizationRun.objects.get(id=response.data["id"])
    assert run.status == OptimizationRunStatus.FAILED
    assert run.completed_at is not None
    assert run.failure_message


@pytest.mark.django_db
@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="csv",
    MARKET_DATA_ALLOWED_PROVIDERS=("csv",),
)
def test_optimization_runs_are_owner_scoped() -> None:
    call_command("seed_sample_portfolio", reset=True, verbosity=0)
    owner = User.objects.get(email=SAMPLE_USER_EMAIL)
    other = User.objects.create_user(email="other@example.test", password="test-password")
    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)

    created = owner_client.post(
        reverse("api-v1-optimization-run-list"),
        {
            "portfolio_id": str(SAMPLE_PORTFOLIO_ID),
            "method": "EQUAL_WEIGHT",
            "start": "2026-03-16",
            "end": "2026-09-16",
            "asset_ids": [str(SAMPLE_AAPL_ID), str(SAMPLE_MSFT_ID)],
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED

    other_client = APIClient()
    other_client.force_authenticate(user=other)
    detail = other_client.get(
        reverse("api-v1-optimization-run-detail", kwargs={"run_id": created.data["id"]})
    )
    create_against_owner_portfolio = other_client.post(
        reverse("api-v1-optimization-run-list"),
        {
            "portfolio_id": str(SAMPLE_PORTFOLIO_ID),
            "method": "EQUAL_WEIGHT",
            "start": "2026-03-16",
            "end": "2026-09-16",
        },
        format="json",
    )

    assert detail.status_code == status.HTTP_404_NOT_FOUND
    assert create_against_owner_portfolio.status_code == status.HTTP_404_NOT_FOUND
