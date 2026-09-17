"""OpenAPI coverage for the Phase 5 optimization-run resource."""

from __future__ import annotations

import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_exposes_optimization_run_contracts() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK
    schema = json.loads(response.content)
    paths = schema["paths"]
    assert paths["/api/v1/optimization-runs/"]["get"]["operationId"] == ("optimization_run_list")
    assert paths["/api/v1/optimization-runs/"]["post"]["operationId"] == ("optimization_run_create")
    assert paths["/api/v1/optimization-runs/{run_id}/"]["get"]["operationId"] == (
        "optimization_run_detail"
    )

    schemas = schema["components"]["schemas"]
    assert "OptimizationRun" in schemas
    assert "OptimizationRunCreateRequest" in schemas
    assert "OptimizationResult" in schemas
