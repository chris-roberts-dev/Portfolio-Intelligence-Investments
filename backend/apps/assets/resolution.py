"""Django-backed canonical asset/provider-symbol resolution.

This adapter is the persistence implementation of the provider-neutral
``AssetResolver`` application protocol. It performs no provider calls and never
rewrites an unresolved canonical symbol into another security.
"""

from __future__ import annotations

from collections.abc import Sequence

from apps.assets.models import AssetProviderSymbol
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    AssetResolutionError,
    AssetResolutionErrorCode,
    AssetResolutionResult,
    InMemoryAssetResolver,
    canonicalize_user_symbols,
)


class DjangoAssetResolver:
    """Resolve canonical symbols from persisted provider-symbol mappings."""

    def resolve(
        self,
        symbols: Sequence[str],
        *,
        provider: str,
    ) -> AssetResolutionResult:
        """Resolve symbols for exactly one normalized provider."""
        normalized_provider = provider.strip().lower()

        if not normalized_provider:
            raise AssetResolutionError(
                AssetResolutionErrorCode.BLANK_PROVIDER,
                "provider must not be blank.",
                provider=normalized_provider,
            )

        requested_symbols = canonicalize_user_symbols(symbols)
        canonical_symbols = tuple(requested_symbol.symbol for requested_symbol in requested_symbols)

        if not canonical_symbols:
            return AssetResolutionResult(
                provider=normalized_provider,
                outcomes=(),
            )

        mappings = (
            AssetProviderSymbol.objects.select_related("asset")
            .filter(
                provider=normalized_provider,
                asset__is_active=True,
                asset__symbol__in=canonical_symbols,
            )
            .order_by("asset__symbol", "id")
        )

        records = tuple(
            AssetProviderSymbolRecord(
                asset_id=mapping.asset_id,
                canonical_symbol=mapping.asset.symbol,
                provider=mapping.provider,
                provider_symbol=mapping.provider_symbol,
            )
            for mapping in mappings
        )

        return InMemoryAssetResolver(records).resolve(
            canonical_symbols,
            provider=normalized_provider,
        )
