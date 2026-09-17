"""Django persistence adapter for discovered canonical assets."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.assets.models import Asset, AssetProviderSymbol, AssetType
from apps.market_data.providers.discovery_base import (
    DiscoveredAssetType,
    DiscoveredProviderAsset,
)
from apps.market_data.services.asset_discovery import (
    AssetCatalogWriteError,
    AssetCatalogWriteErrorCode,
)


class DjangoDiscoveredAssetCatalog:
    """Persist supported discovered securities without provider-side substitution."""

    @transaction.atomic
    def persist(
        self,
        discovered: DiscoveredProviderAsset,
        *,
        provider: str,
    ):
        """Reuse or create canonical identity and exactly one provider mapping."""
        normalized_provider = provider.strip().lower()

        if not normalized_provider:
            raise ValueError("provider must not be blank.")

        existing_mapping = (
            AssetProviderSymbol.objects.select_for_update()
            .select_related("asset")
            .filter(
                provider=normalized_provider,
                provider_symbol=discovered.provider_symbol,
            )
            .first()
        )

        if existing_mapping is not None:
            asset = existing_mapping.asset

            if (
                asset.symbol != discovered.canonical_symbol
                or not asset.is_active
                or asset.currency != discovered.currency
                or asset.asset_type != discovered.asset_type.value
            ):
                raise AssetCatalogWriteError(
                    AssetCatalogWriteErrorCode.PROVIDER_SYMBOL_CONFLICT,
                    (
                        f"Provider symbol {discovered.provider_symbol!r} is already "
                        "mapped to an incompatible canonical asset."
                    ),
                )

            return asset.id

        candidates = tuple(
            Asset.objects.select_for_update()
            .filter(symbol=discovered.canonical_symbol)
            .order_by("id")
        )
        eligible = tuple(
            candidate
            for candidate in candidates
            if candidate.is_active
            and candidate.currency == discovered.currency
            and candidate.asset_type == discovered.asset_type.value
        )

        if len(eligible) > 1:
            raise AssetCatalogWriteError(
                AssetCatalogWriteErrorCode.AMBIGUOUS_CANONICAL_ASSET,
                (
                    f"Multiple active canonical assets already use symbol "
                    f"{discovered.canonical_symbol!r}."
                ),
            )

        if eligible:
            asset = eligible[0]
        elif candidates:
            raise AssetCatalogWriteError(
                AssetCatalogWriteErrorCode.EXISTING_CANONICAL_ASSET_UNSUPPORTED,
                (
                    f"Existing canonical asset {discovered.canonical_symbol!r} "
                    "is inactive or conflicts with discovered type/currency."
                ),
            )
        else:
            asset_type = (
                AssetType.STOCK
                if discovered.asset_type is DiscoveredAssetType.STOCK
                else AssetType.ETF
            )
            asset = Asset(
                symbol=discovered.canonical_symbol,
                name=discovered.name,
                asset_type=asset_type,
                exchange=discovered.exchange,
                currency=discovered.currency,
                is_active=True,
            )

            try:
                asset.full_clean()
                asset.save()
            except ValidationError as exc:
                raise AssetCatalogWriteError(
                    AssetCatalogWriteErrorCode.PERSISTENCE_VALIDATION_FAILED,
                    (
                        f"Discovered canonical asset {discovered.canonical_symbol!r} "
                        "failed model validation."
                    ),
                ) from exc

        mapping = AssetProviderSymbol(
            asset=asset,
            provider=normalized_provider,
            provider_symbol=discovered.provider_symbol,
            is_primary=not AssetProviderSymbol.objects.filter(
                asset=asset,
                provider=normalized_provider,
                is_primary=True,
            ).exists(),
            verified_at=timezone.now(),
        )

        try:
            mapping.full_clean()
            mapping.save()
        except ValidationError as exc:
            raise AssetCatalogWriteError(
                AssetCatalogWriteErrorCode.PERSISTENCE_VALIDATION_FAILED,
                (f"Provider mapping for {discovered.canonical_symbol!r} failed model validation."),
            ) from exc

        return asset.id
