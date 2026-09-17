"""Provider-neutral discovery-adapter registry."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType

from apps.market_data.providers.discovery_base import AssetDiscoveryProvider
from apps.market_data.providers.yfinance_discovery import (
    YFinanceAssetDiscoveryProvider,
)

type AssetDiscoveryProviderFactory = Callable[[], AssetDiscoveryProvider]

REGISTERED_ASSET_DISCOVERY_FACTORIES: Mapping[
    str,
    AssetDiscoveryProviderFactory,
] = MappingProxyType(
    {
        "yfinance": YFinanceAssetDiscoveryProvider,
    }
)


def resolve_asset_discovery_provider(
    provider_name: str,
    *,
    factories: Mapping[
        str,
        AssetDiscoveryProviderFactory,
    ] = REGISTERED_ASSET_DISCOVERY_FACTORIES,
) -> AssetDiscoveryProvider | None:
    """Return the discovery adapter for a provider, when one is supported."""
    normalized_provider = provider_name.strip().lower()

    if not normalized_provider:
        raise ValueError("provider_name must not be blank.")

    factory = factories.get(normalized_provider)

    if factory is None:
        return None

    return factory()
