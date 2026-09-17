"""Integration coverage for canonical persistence of discovered provider assets."""

from __future__ import annotations

from uuid import UUID

import pytest

from apps.assets.discovery import DjangoDiscoveredAssetCatalog
from apps.assets.models import Asset, AssetProviderSymbol, AssetType
from apps.market_data.providers.discovery_base import (
    DiscoveredAssetType,
    DiscoveredProviderAsset,
)
from apps.market_data.services.asset_discovery import (
    AssetCatalogWriteError,
    AssetCatalogWriteErrorCode,
)

EXISTING_ID = UUID("00000000-0000-0000-0000-000000000201")


def discovered_qqq() -> DiscoveredProviderAsset:
    return DiscoveredProviderAsset(
        requested_symbol="QQQ",
        canonical_symbol="QQQ",
        provider_symbol="QQQ",
        name="Invesco QQQ Trust",
        asset_type=DiscoveredAssetType.ETF,
        exchange="NasdaqGM",
        currency="USD",
    )


@pytest.mark.django_db
def test_catalog_creates_supported_asset_and_yfinance_mapping() -> None:
    asset_id = DjangoDiscoveredAssetCatalog().persist(
        discovered_qqq(),
        provider="YFINANCE",
    )

    asset = Asset.objects.get(id=asset_id)
    mapping = AssetProviderSymbol.objects.get(
        provider="yfinance",
        provider_symbol="QQQ",
    )

    assert asset.symbol == "QQQ"
    assert asset.name == "Invesco QQQ Trust"
    assert asset.asset_type == AssetType.ETF
    assert asset.currency == "USD"
    assert asset.is_active
    assert mapping.asset == asset
    assert mapping.is_primary
    assert mapping.verified_at is not None


@pytest.mark.django_db
def test_catalog_reuses_existing_supported_canonical_asset() -> None:
    existing = Asset.objects.create(
        id=EXISTING_ID,
        symbol="QQQ",
        name="Existing QQQ",
        asset_type=AssetType.ETF,
        exchange="NASDAQ",
        currency="USD",
        is_active=True,
    )

    asset_id = DjangoDiscoveredAssetCatalog().persist(
        discovered_qqq(),
        provider="yfinance",
    )

    assert asset_id == existing.id
    assert Asset.objects.filter(symbol="QQQ").count() == 1
    assert AssetProviderSymbol.objects.filter(
        asset=existing,
        provider="yfinance",
        provider_symbol="QQQ",
    ).exists()


@pytest.mark.django_db
def test_catalog_rejects_ambiguous_existing_symbol() -> None:
    for suffix in (1, 2):
        Asset.objects.create(
            symbol="QQQ",
            name=f"QQQ {suffix}",
            asset_type=AssetType.ETF,
            exchange="NASDAQ",
            currency="USD",
            is_active=True,
        )

    with pytest.raises(AssetCatalogWriteError) as exc_info:
        DjangoDiscoveredAssetCatalog().persist(
            discovered_qqq(),
            provider="yfinance",
        )

    assert exc_info.value.code is AssetCatalogWriteErrorCode.AMBIGUOUS_CANONICAL_ASSET


@pytest.mark.django_db
def test_catalog_never_reuses_incompatible_existing_symbol() -> None:
    Asset.objects.create(
        symbol="QQQ",
        name="Inactive QQQ",
        asset_type=AssetType.ETF,
        exchange="NASDAQ",
        currency="USD",
        is_active=False,
    )

    with pytest.raises(AssetCatalogWriteError) as exc_info:
        DjangoDiscoveredAssetCatalog().persist(
            discovered_qqq(),
            provider="yfinance",
        )

    assert exc_info.value.code is AssetCatalogWriteErrorCode.EXISTING_CANONICAL_ASSET_UNSUPPORTED
