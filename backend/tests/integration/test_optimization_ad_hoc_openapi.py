from __future__ import annotations

import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_exposes_standalone_allocation_lab_contracts() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )
    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    paths = schema["paths"]

    assert paths["/api/v1/assets/resolve/"]["post"]["operationId"] == "asset_catalog_resolve"
    assert paths["/api/v1/optimization-runs/"]["post"]["operationId"] == "optimization_run_create"

    schemas = schema["components"]["schemas"]
    request = schemas["OptimizationRunCreateRequest"]
    properties = request["properties"]

    assert "source_type" in properties
    assert "portfolio_id" in properties
    assert "baseline_weights" in properties
    assert "risk_free_rate_annual" in properties
    assert "asset_ids" in properties

    response_schema = schemas["OptimizationRun"]
    response_properties = response_schema["properties"]
    assert "source_type" in response_properties
    assert "portfolio_id" in response_properties
    assert "portfolio_name" in response_properties
    assert "baseline_weights" in response_properties
