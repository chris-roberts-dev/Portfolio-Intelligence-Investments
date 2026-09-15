"""OpenAPI regression coverage for the canonical dashboard snapshot."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_exposes_dashboard_snapshot_contract() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    operation = schema["paths"]["/api/v1/portfolios/{portfolio_id}/dashboard/"]["get"]

    assert operation["operationId"] == "portfolio_dashboard_snapshot"
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

    assert "DashboardSnapshotResult" in components
    assert "DashboardSnapshotContext" in components
    assert "DashboardSnapshotModuleState" in components
