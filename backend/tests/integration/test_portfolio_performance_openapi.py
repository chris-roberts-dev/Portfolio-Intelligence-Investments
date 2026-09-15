"""OpenAPI regression coverage for dashboard portfolio performance."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_exposes_portfolio_performance_contract() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    operation = schema["paths"]["/api/v1/portfolios/{portfolio_id}/performance/"]["get"]

    assert operation["operationId"] == "portfolio_performance"
    assert operation["tags"] == ["portfolios"]
    assert set(operation["responses"]) == {
        "200",
        "400",
        "403",
        "404",
        "429",
        "503",
    }

    component_schemas = schema["components"]["schemas"]

    assert "DashboardPerformanceResult" in component_schemas
    assert "PortfolioPerformancePoint" in component_schemas
    assert "BenchmarkPerformancePoint" in component_schemas
    assert "DashboardPerformanceProvenance" in component_schemas
