"""OpenAPI regression tests for owned-portfolio read endpoints."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_schema_exposes_owned_portfolio_read_contracts() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    paths = schema["paths"]

    portfolio_list = paths["/api/v1/portfolios/"]["get"]
    portfolio_detail = paths["/api/v1/portfolios/{portfolio_id}/"]["get"]
    portfolio_delete = paths["/api/v1/portfolios/{portfolio_id}/"]["delete"]
    holdings = paths["/api/v1/portfolios/{portfolio_id}/holdings/"]["get"]
    analytics = paths["/api/v1/analytics/portfolios/{portfolio_id}/"]["get"]

    assert portfolio_list["operationId"] == "portfolio_list"
    assert portfolio_list["tags"] == ["portfolios"]
    assert set(portfolio_list["responses"]) == {"200"}

    assert portfolio_detail["operationId"] == "portfolio_detail"
    assert set(portfolio_detail["responses"]) == {"200", "404"}

    assert portfolio_delete["operationId"] == "portfolio_delete"
    assert portfolio_delete["tags"] == ["portfolios"]
    assert set(portfolio_delete["responses"]) == {"204", "404", "409"}

    assert holdings["operationId"] == "portfolio_current_holdings"
    assert holdings["tags"] == ["portfolios"]
    assert set(holdings["responses"]) == {
        "200",
        "400",
        "403",
        "404",
        "429",
        "503",
    }

    assert analytics["operationId"] == "portfolio_analytics"
    assert analytics["tags"] == ["analytics"]
    assert set(analytics["responses"]) == {
        "200",
        "400",
        "403",
        "404",
        "429",
        "503",
    }

    component_schemas = schema["components"]["schemas"]

    assert "PortfolioSummary" in component_schemas
    assert "CurrentPortfolioHoldings" in component_schemas
    assert "PortfolioAnalyticsResult" in component_schemas
    assert "AnalyticalResultProvenance" in component_schemas
    assert "PortfolioValidationError" in component_schemas
    assert "PortfolioApiError" in component_schemas
