"""Integration tests for provider-secret safety at the market-bar API boundary."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.market_data.api import views
from apps.market_data.providers.base import ProviderIssue
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.providers.safety import REDACTED_PROVIDER_VALUE
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    InMemoryAssetResolver,
)

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)
SECRET = "portfolio-api-secret-456"


class AuthenticatedUser:
    """Minimal authenticated principal for API transport tests."""

    pk = 1
    is_authenticated = True
    is_staff = False


def authenticated_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=AuthenticatedUser())
    return client


def request_payload() -> dict[str, object]:
    return {
        "symbols": ["AAPL"],
        "start": "2026-01-01",
        "end": "2026-01-04",
        "interval": "1d",
        "provider": "mock",
    }


def test_provider_issue_secret_is_not_serialized_or_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    resolver = InMemoryAssetResolver(
        (
            AssetProviderSymbolRecord(
                asset_id=ASSET_ID,
                canonical_symbol="AAPL",
                provider="mock",
                provider_symbol="AAPL",
            ),
        )
    )
    provider = MockMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
        issues={
            ASSET_ID: ProviderIssue(
                code="FAILED",
                message=f"client_secret={SECRET}",
            )
        },
    )

    monkeypatch.setattr(
        views,
        "get_asset_resolver",
        lambda: resolver,
    )
    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        lambda _requested_provider=None, **_kwargs: provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        request_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["status"] == "FAILED"
    assert SECRET not in str(response.data)
    assert REDACTED_PROVIDER_VALUE in str(response.data["results"][0]["warnings"])
    assert all(SECRET not in record.getMessage() for record in caplog.records)


def test_provider_initialization_secret_is_not_serialized_or_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_provider_resolution(
        _requested_provider=None,
        **_kwargs,
    ):
        raise RuntimeError(f"Authorization: Bearer {SECRET}")

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        fail_provider_resolution,
    )

    payload = request_payload()
    payload.pop("provider")

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data["code"] == "PROVIDER_INITIALIZATION_FAILED"
    assert SECRET not in str(response.data)
    assert REDACTED_PROVIDER_VALUE in response.data["detail"]
    assert all(SECRET not in record.getMessage() for record in caplog.records)
