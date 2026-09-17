"""Integration tests for live symbol discovery before canonical market-bar retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from types import MappingProxyType

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.assets.discovery import DjangoDiscoveredAssetCatalog
from apps.assets.models import Asset, AssetProviderSymbol, AssetType
from apps.assets.resolution import DjangoAssetResolver
from apps.market_data.api import views
from apps.market_data.providers.base import (
    ProviderBatchResult,
    ResolvedProviderAsset,
)
from apps.market_data.providers.discovery_base import (
    AssetDiscoveryIssue,
    AssetDiscoveryIssueCode,
    AssetDiscoveryProvider,
    AssetDiscoveryResult,
    DiscoveredAssetType,
    DiscoveredProviderAsset,
)
from portfolio_engine.contracts.market_data import PriceBar

RETRIEVED_AT = datetime(2026, 9, 17, 10, 30, tzinfo=UTC)


class AuthenticatedUser:
    is_authenticated = True
    is_staff = False
    pk = 9999


class DeterministicDiscoveryProvider:
    name = "yfinance"

    def __init__(
        self,
        outcomes: dict[
            str,
            DiscoveredProviderAsset | AssetDiscoveryIssue,
        ],
    ) -> None:
        self._outcomes = outcomes
        self.calls: list[tuple[str, ...]] = []

    def discover(
        self,
        symbols: Sequence[str],
    ) -> AssetDiscoveryResult:
        normalized = tuple(symbol.strip().upper() for symbol in symbols)
        self.calls.append(normalized)
        return AssetDiscoveryResult(
            provider=self.name,
            outcomes=tuple(self._outcomes[symbol] for symbol in normalized),
        )


class DeterministicYFinanceBars:
    name = "yfinance"

    def __init__(self) -> None:
        self.calls: list[tuple[ResolvedProviderAsset, ...]] = []

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        batch = tuple(assets)
        self.calls.append(batch)
        frames = {
            asset.asset_id: (
                PriceBar(
                    asset_id=asset.asset_id,
                    trade_date=start,
                    open=100.0,
                    high=102.0,
                    low=99.0,
                    close=101.0,
                    adjusted_close=101.0,
                    volume=1_000_000,
                    source=self.name,
                    retrieved_at=RETRIEVED_AT,
                ),
            )
            for asset in batch
        }

        return ProviderBatchResult(
            frames=MappingProxyType(frames),
            issues=MappingProxyType({}),
            retrieved_at=RETRIEVED_AT,
        )


def discovered(
    symbol: str,
    *,
    asset_type: DiscoveredAssetType = DiscoveredAssetType.STOCK,
) -> DiscoveredProviderAsset:
    return DiscoveredProviderAsset(
        requested_symbol=symbol,
        canonical_symbol=symbol,
        provider_symbol=symbol,
        name=f"{symbol} Security",
        asset_type=asset_type,
        exchange="NASDAQ",
        currency="USD",
    )


def authenticated_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=AuthenticatedUser())
    return client


def install_live_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    discovery_provider: AssetDiscoveryProvider,
    price_provider: DeterministicYFinanceBars,
) -> None:
    monkeypatch.setattr(
        views,
        "get_asset_resolver",
        DjangoAssetResolver,
    )
    monkeypatch.setattr(
        views,
        "get_asset_catalog_writer",
        DjangoDiscoveredAssetCatalog,
    )
    monkeypatch.setattr(
        views,
        "get_asset_discovery_provider",
        lambda _provider_name: discovery_provider,
    )
    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        lambda _requested_provider=None, **_kwargs: price_provider,
    )


def payload(*symbols: str) -> dict[str, object]:
    return {
        "symbols": list(symbols),
        "start": "2026-08-03",
        "end": "2026-08-04",
        "interval": "1d",
    }


@pytest.mark.django_db
def test_known_yfinance_asset_skips_discovery_and_uses_existing_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asset = Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
        is_active=True,
    )
    AssetProviderSymbol.objects.create(
        asset=asset,
        provider="yfinance",
        provider_symbol="AAPL",
        is_primary=True,
    )
    discovery_provider = DeterministicDiscoveryProvider({})
    price_provider = DeterministicYFinanceBars()
    install_live_dependencies(
        monkeypatch,
        discovery_provider=discovery_provider,
        price_provider=price_provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload("AAPL"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["status"] == "SUCCEEDED"
    assert response.data["results"][0]["asset_id"] == str(asset.id)
    assert discovery_provider.calls == []
    assert tuple(asset.canonical_symbol for asset in price_provider.calls[0]) == ("AAPL",)


@pytest.mark.django_db
def test_unknown_supported_yfinance_symbol_is_onboarded_then_queried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovery_provider = DeterministicDiscoveryProvider(
        {"QQQ": discovered("QQQ", asset_type=DiscoveredAssetType.ETF)}
    )
    price_provider = DeterministicYFinanceBars()
    install_live_dependencies(
        monkeypatch,
        discovery_provider=discovery_provider,
        price_provider=price_provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload("QQQ"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["status"] == "SUCCEEDED"
    assert response.data["results"][0]["asset_id"] is not None
    assert response.data["meta"]["provider"] == "yfinance"
    assert discovery_provider.calls == [("QQQ",)]
    assert len(price_provider.calls) == 1
    assert tuple(asset.canonical_symbol for asset in price_provider.calls[0]) == ("QQQ",)
    assert Asset.objects.filter(symbol="QQQ", is_active=True).exists()
    assert AssetProviderSymbol.objects.filter(
        asset__symbol="QQQ",
        provider="yfinance",
        provider_symbol="QQQ",
    ).exists()


@pytest.mark.django_db
def test_fourteen_unknown_symbols_are_discovered_and_downloaded_in_one_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symbols = (
        "QQQ",
        "NVDA",
        "AMD",
        "GOOGL",
        "META",
        "JPM",
        "V",
        "COST",
        "AVGO",
        "NFLX",
        "ADBE",
        "CRM",
        "ORCL",
        "INTC",
    )
    discovery_provider = DeterministicDiscoveryProvider(
        {symbol: discovered(symbol) for symbol in symbols}
    )
    price_provider = DeterministicYFinanceBars()
    install_live_dependencies(
        monkeypatch,
        discovery_provider=discovery_provider,
        price_provider=price_provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload(*symbols),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["symbol"] for item in response.data["results"]] == list(symbols)
    assert {item["status"] for item in response.data["results"]} == {"SUCCEEDED"}
    assert discovery_provider.calls == [symbols]
    assert len(price_provider.calls) == 1
    assert tuple(asset.canonical_symbol for asset in price_provider.calls[0]) == symbols
    assert response.data["row_count"] == 14


@pytest.mark.django_db
def test_invalid_discovered_symbol_remains_not_found_with_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovery_provider = DeterministicDiscoveryProvider(
        {
            "BAD": AssetDiscoveryIssue(
                requested_symbol="BAD",
                code=AssetDiscoveryIssueCode.NOT_FOUND,
                message="yfinance did not find an exact symbol match for BAD.",
            )
        }
    )
    price_provider = DeterministicYFinanceBars()
    install_live_dependencies(
        monkeypatch,
        discovery_provider=discovery_provider,
        price_provider=price_provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload("BAD"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.data["results"][0]
    assert result["status"] == "NOT_FOUND"
    assert result["asset_id"] is None
    assert result["warnings"] == ["yfinance did not find an exact symbol match for BAD."]
    assert price_provider.calls == [()]


@pytest.mark.django_db
def test_unsupported_instrument_remains_not_found_without_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovery_provider = DeterministicDiscoveryProvider(
        {
            "BTC-USD": AssetDiscoveryIssue(
                requested_symbol="BTC-USD",
                code=AssetDiscoveryIssueCode.UNSUPPORTED_ASSET_TYPE,
                message=(
                    "BTC-USD is a yfinance CRYPTOCURRENCY instrument; "
                    "only STOCK and ETF assets are supported."
                ),
            )
        }
    )
    price_provider = DeterministicYFinanceBars()
    install_live_dependencies(
        monkeypatch,
        discovery_provider=discovery_provider,
        price_provider=price_provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload("BTC-USD"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    result = response.data["results"][0]
    assert result["status"] == "NOT_FOUND"
    assert "only STOCK and ETF" in result["warnings"][0]
    assert not Asset.objects.filter(symbol="BTC-USD").exists()


@pytest.mark.django_db
def test_discovery_provider_failure_is_failed_without_blocking_valid_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovery_provider = DeterministicDiscoveryProvider(
        {
            "QQQ": discovered("QQQ", asset_type=DiscoveredAssetType.ETF),
            "BROKEN": AssetDiscoveryIssue(
                requested_symbol="BROKEN",
                code=AssetDiscoveryIssueCode.PROVIDER_ERROR,
                message="yfinance asset discovery failed for BROKEN.",
            ),
        }
    )
    price_provider = DeterministicYFinanceBars()
    install_live_dependencies(
        monkeypatch,
        discovery_provider=discovery_provider,
        price_provider=price_provider,
    )

    response = authenticated_client().post(
        reverse("api-v1-market-data-bars-query"),
        payload("QQQ", "BROKEN"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["status"] for item in response.data["results"]] == [
        "SUCCEEDED",
        "FAILED",
    ]
    assert response.data["results"][1]["warnings"] == [
        "yfinance asset discovery failed for BROKEN."
    ]
    assert tuple(asset.canonical_symbol for asset in price_provider.calls[0]) == ("QQQ",)
