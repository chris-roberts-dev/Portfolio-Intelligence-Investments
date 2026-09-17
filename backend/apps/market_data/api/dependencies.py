"""Dependency boundary for market-data API application services."""

from apps.assets.discovery import DjangoDiscoveredAssetCatalog
from apps.assets.resolution import DjangoAssetResolver
from apps.market_data.providers.discovery_base import AssetDiscoveryProvider
from apps.market_data.providers.discovery_configuration import (
    resolve_asset_discovery_provider,
)
from apps.market_data.services.asset_discovery import AssetCatalogWriter
from apps.market_data.services.asset_resolution import AssetResolver


def get_asset_resolver() -> AssetResolver:
    """Return the persisted canonical asset/provider-symbol resolver."""
    return DjangoAssetResolver()


def get_asset_discovery_provider(
    provider_name: str,
) -> AssetDiscoveryProvider | None:
    """Return an optional live discovery adapter for the selected provider."""
    return resolve_asset_discovery_provider(provider_name)


def get_asset_catalog_writer() -> AssetCatalogWriter:
    """Return the canonical persistence adapter for discovered securities."""
    return DjangoDiscoveredAssetCatalog()
