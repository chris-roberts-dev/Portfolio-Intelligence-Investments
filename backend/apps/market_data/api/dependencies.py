"""Dependency boundary for market-data API application services."""

from apps.assets.resolution import DjangoAssetResolver
from apps.market_data.services.asset_resolution import AssetResolver


def get_asset_resolver() -> AssetResolver:
    """Return the persisted canonical asset/provider-symbol resolver."""
    return DjangoAssetResolver()
