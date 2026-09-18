"""OpenAPI regression tests for Phase 4 portfolio/transaction mutations."""

from __future__ import annotations

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


def test_openapi_exposes_portfolio_and_transaction_ingestion_contracts() -> None:
    response = APIClient().get(
        reverse("api-v1-schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == status.HTTP_200_OK
    schema = json.loads(response.content)
    paths = schema["paths"]

    assert paths["/api/v1/portfolios/"]["post"]["operationId"] == "portfolio_create"
    assert paths["/api/v1/portfolios/{portfolio_id}/"]["patch"]["operationId"] == (
        "portfolio_rename"
    )
    assert (
        paths["/api/v1/portfolios/{portfolio_id}/benchmark/"]["patch"]["operationId"]
        == "portfolio_benchmark_update"
    )
    assert paths["/api/v1/assets/"]["get"]["operationId"] == "asset_catalog_list"
    transaction_collection = paths["/api/v1/portfolios/{portfolio_id}/transactions/"]
    assert transaction_collection["get"]["operationId"] == "portfolio_transaction_list"
    assert set(transaction_collection["get"]["responses"]) == {"200", "404"}
    assert transaction_collection["post"]["operationId"] == "portfolio_transaction_create"
    preview_import = paths["/api/v1/portfolios/{portfolio_id}/transactions/import/preview/"]["post"]
    confirm_import = paths["/api/v1/portfolios/{portfolio_id}/transactions/import/confirm/"]["post"]

    assert preview_import["operationId"] == "portfolio_transaction_import_preview"
    assert set(preview_import["responses"]) == {"200", "400", "404", "503"}
    assert "asset_symbol" in preview_import["description"]

    assert confirm_import["operationId"] == "portfolio_transaction_import_confirm"
    assert set(confirm_import["responses"]) == {"201", "400", "404", "503"}
    assert "Re-resolve ticker symbols" in confirm_import["description"]

    schemas = schema["components"]["schemas"]
    assert "PortfolioCreateRequest" in schemas
    assert "PatchedPortfolioRenameRequest" in schemas
    assert "PatchedPortfolioBenchmarkRequest" in schemas
    assert "PortfolioTransactionCreateRequest" in schemas
    assert "PortfolioTransaction" in schemas
    assert "TransactionImportRequest" in schemas
    assert "TransactionImportPreview" in schemas
    assert "TransactionImportResult" in schemas

    benchmark_request_ref = paths["/api/v1/portfolios/{portfolio_id}/benchmark/"]["patch"][
        "requestBody"
    ]["content"]["application/json"]["schema"]["$ref"]
    assert benchmark_request_ref.endswith("/PatchedPortfolioBenchmarkRequest")
