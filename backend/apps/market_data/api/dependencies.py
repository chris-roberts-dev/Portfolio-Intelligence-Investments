"""Dependency boundary for market-data API application services."""

from apps.market_data.services.asset_resolution import (
    AssetResolver,
    InMemoryAssetResolver,
)


def get_asset_resolver() -> AssetResolver:
    """Return the current resolver implementation for the API boundary.

    Persistent asset/provider-symbol resolution is introduced with the asset
    persistence phase. Until then, the API depends on the resolver protocol and
    uses an empty deterministic resolver rather than embedding symbol mappings.
    """
    return InMemoryAssetResolver(())
