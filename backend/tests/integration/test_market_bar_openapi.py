"""OpenAPI regression tests for the versioned market-bar query endpoint."""

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_schema_exposes_market_bar_query_contract() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK

    schema = json.loads(response.content)
    path_item = schema["paths"]["/api/v1/market-data/bars/query/"]
    operation = path_item["post"]

    assert "get" not in path_item
    assert operation["operationId"] == "market_data_bars_query"
    assert operation["tags"] == ["market-data"]
    assert set(operation["responses"]) == {
        "200",
        "400",
        "403",
        "429",
        "503",
    }
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/MarketBarQuery"
    }

    component_schemas = schema["components"]["schemas"]

    assert "MarketBarQuery" in component_schemas
    assert "MarketBarBatchResult" in component_schemas
    assert "MarketBarValidationError" in component_schemas
    assert "MarketBarApiError" in component_schemas
    assert "MarketBarBadGatewayResponse" not in component_schemas
