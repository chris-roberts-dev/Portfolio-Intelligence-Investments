"""OpenAPI regression coverage for the P0 allocation endpoint."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_exposes_dashboard_allocation_contract() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    operation = schema["paths"]["/api/v1/portfolios/{portfolio_id}/allocation/"]["get"]

    assert operation["operationId"] == "portfolio_dashboard_allocation"
    assert operation["tags"] == ["portfolios"]
    assert set(operation["responses"]) == {
        "200",
        "400",
        "403",
        "404",
        "429",
        "503",
    }

    components = schema["components"]["schemas"]

    assert "DashboardAllocationResult" in components
    assert "DashboardAllocationGroup" in components
    assert "DashboardAllocationTotals" in components
    assert "DashboardAllocationProvenance" in components
