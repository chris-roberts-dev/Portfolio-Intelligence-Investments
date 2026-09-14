"""Integration tests for the versioned market-bar query API."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.market_data.api import views
from apps.market_data.providers.base import ProviderIssue
from apps.market_data.providers.configuration import (
    ProviderConfigurationError,
    ProviderConfigurationErrorCode,
)
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    InMemoryAssetResolver,
)
from portfolio_engine.contracts.market_data import PriceBar

AAPL_ID = UUID("00000000-0000-0000-0000-000000000001")
EMPTY_ID = UUID("00000000-0000-0000-0000-000000000002")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)


class AuthenticatedUser:
    """Minimal authenticated principal for transport-layer API tests."""

    is_authenticated = True

    def __init__(
        self,
        *,
        pk: int = 1,
        is_staff: bool = False,
    ) -> None:
        self.pk = pk
        self.is_staff = is_staff


class YFinanceTestProvider(MockMarketDataProvider):
    """Deterministic non-network provider carrying the yfinance provider name."""

    name = "yfinance"


def authenticated_client(
    *,
    pk: int = 1,
    is_staff: bool = False,
) -> APIClient:
    client = APIClient()
    client.force_authenticate(
        user=AuthenticatedUser(
            pk=pk,
            is_staff=is_staff,
        )
    )
    return client


def resolver_with_aapl_and_empty(
    *,
    provider: str = "mock",
) -> InMemoryAssetResolver:
    return InMemoryAssetResolver(
        (
            AssetProviderSymbolRecord(
                asset_id=AAPL_ID,
                canonical_symbol="AAPL",
                provider=provider,
                provider_symbol="AAPL",
            ),
            AssetProviderSymbolRecord(
                asset_id=EMPTY_ID,
                canonical_symbol="EMPTY",
                provider=provider,
                provider_symbol="EMPTY",
            ),
        )
    )


def aapl_bar(
    *,
    source: str = "mock",
) -> PriceBar:
    return PriceBar(
        asset_id=AAPL_ID,
        trade_date=date(2026, 1, 2),
        open=100.0,
        high=103.0,
        low=99.0,
        close=102.0,
        adjusted_close=101.5,
        volume=1_000_000,
        source=source,
        retrieved_at=RETRIEVED_AT,
    )


def install_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    resolver: InMemoryAssetResolver,
    provider: MockMarketDataProvider,
) -> None:
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


def request_payload(*symbols: str) -> dict[str, object]:
    return {
        "symbols": list(symbols),
        "start": "2026-01-01",
        "end": "2026-01-04",
        "interval": "1d",
        "provider": "mock",
    }


def test_market_bar_query_returns_200_when_every_symbol_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MockMarketDataProvider(
        {
            AAPL_ID: (aapl_bar(),),
        },
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(),
        provider=provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        request_payload("AAPL"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["status"] == "SUCCEEDED"
    assert response.data["meta"]["provider"] == "mock"
    assert response.data["row_count"] == 1


def test_market_bar_query_returns_200_for_mixed_symbol_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MockMarketDataProvider(
        {
            AAPL_ID: (aapl_bar(),),
        },
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(),
        provider=provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        request_payload("AAPL", "UNKNOWN"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["status"] for item in response.data["results"]] == [
        "SUCCEEDED",
        "NOT_FOUND",
    ]


def test_market_bar_query_returns_200_when_every_symbol_is_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MockMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=InMemoryAssetResolver(()),
        provider=provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        request_payload("UNKNOWN", "MISSING"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["status"] for item in response.data["results"]] == [
        "NOT_FOUND",
        "NOT_FOUND",
    ]


def test_market_bar_query_returns_200_for_no_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MockMarketDataProvider(
        {
            EMPTY_ID: (),
        },
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(),
        provider=provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        request_payload("EMPTY"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["status"] == "NO_DATA"


def test_market_bar_query_returns_200_when_provider_reports_symbol_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MockMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
        issues={
            AAPL_ID: ProviderIssue(
                code="FAILED",
                message="Configured deterministic provider failure.",
            )
        },
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(),
        provider=provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        request_payload("AAPL"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["status"] == "FAILED"


def test_market_bar_query_returns_400_for_request_validation_failure() -> None:
    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        {
            "symbols": ["AAPL"],
            "start": "2026-01-04",
            "end": "2026-01-04",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "end" in response.data["errors"]


def test_default_provider_is_available_to_non_staff_authenticated_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MockMarketDataProvider(
        {
            AAPL_ID: (aapl_bar(),),
        },
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(),
        provider=provider,
    )

    payload = request_payload("AAPL")
    payload.pop("provider")

    response = authenticated_client(is_staff=False).post(
        reverse("api-v1-market-data-bars-query"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK


@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="mock",
    MARKET_DATA_ALLOWED_PROVIDERS=("mock", "yfinance"),
)
def test_staff_user_may_request_allowed_non_default_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = YFinanceTestProvider(
        {
            AAPL_ID: (aapl_bar(source="yfinance"),),
        },
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(provider="yfinance"),
        provider=provider,
    )

    payload = request_payload("AAPL")
    payload["provider"] = "yfinance"

    response = authenticated_client(is_staff=True).post(
        reverse("api-v1-market-data-bars-query"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["meta"]["provider"] == "yfinance"


@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="mock",
    MARKET_DATA_ALLOWED_PROVIDERS=("mock", "yfinance"),
)
def test_non_staff_user_cannot_request_non_default_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_resolution_called = False

    def fail_if_resolved(
        _requested_provider=None,
        **_kwargs,
    ):
        nonlocal provider_resolution_called
        provider_resolution_called = True
        raise AssertionError("provider resolution should not be attempted")

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        fail_if_resolved,
    )

    payload = request_payload("AAPL")
    payload["provider"] = "yfinance"

    response = authenticated_client(is_staff=False).post(
        reverse("api-v1-market-data-bars-query"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "NON_DEFAULT_PROVIDER_FORBIDDEN"
    assert not provider_resolution_called


@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="mock",
    MARKET_DATA_ALLOWED_PROVIDERS=("mock", "yfinance"),
)
def test_authorized_user_still_cannot_bypass_provider_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_provider(
        _requested_provider=None,
        **_kwargs,
    ):
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.PROVIDER_NOT_ALLOWED,
            "Provider 'other' is not allowed.",
            provider_name="other",
        )

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        reject_provider,
    )

    payload = request_payload("AAPL")
    payload["provider"] = "other"

    response = authenticated_client(is_staff=True).post(
        reverse("api-v1-market-data-bars-query"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "PROVIDER_NOT_ALLOWED"
    assert "provider" in response.data["errors"]


def test_market_bar_query_returns_503_when_default_provider_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_provider(
        _requested_provider=None,
        **_kwargs,
    ):
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.DEFAULT_PROVIDER_UNREGISTERED,
            "Configured default provider is unavailable.",
            provider_name="yfinance",
        )

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        unavailable_provider,
    )

    payload = request_payload("AAPL")
    payload.pop("provider")

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data == {
        "code": "DEFAULT_PROVIDER_UNREGISTERED",
        "detail": "Configured default provider is unavailable.",
    }


@override_settings(MARKET_DATA_BAR_QUERY_THROTTLE_RATE="1/min")
def test_market_bar_query_is_throttled_per_authenticated_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache.clear()

    provider = MockMarketDataProvider(
        {
            AAPL_ID: (aapl_bar(),),
        },
        retrieved_at=RETRIEVED_AT,
    )
    install_dependencies(
        monkeypatch,
        resolver=resolver_with_aapl_and_empty(),
        provider=provider,
    )
    client = authenticated_client(pk=999)

    try:
        first_response = client.post(
            reverse("api-v1-market-data-bars-query"),
            request_payload("AAPL"),
            format="json",
        )
        second_response = client.post(
            reverse("api-v1-market-data-bars-query"),
            request_payload("AAPL"),
            format="json",
        )
    finally:
        cache.clear()

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
