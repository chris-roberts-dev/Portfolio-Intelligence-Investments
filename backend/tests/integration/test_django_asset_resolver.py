"""Integration tests for persisted asset/provider-symbol resolution."""

from uuid import UUID

import pytest

from apps.assets.models import Asset, AssetProviderSymbol, AssetType
from apps.assets.resolution import DjangoAssetResolver
from apps.market_data.providers.base import ResolvedProviderAsset
from apps.market_data.services.asset_resolution import (
    AssetResolutionError,
    AssetResolutionErrorCode,
    AssetResolver,
    CanonicalUserSymbol,
    ResolvedAssetSymbol,
    UnresolvedAssetSymbol,
)

AAPL_ID = UUID("00000000-0000-0000-0000-000000000101")
BRKB_ID = UUID("00000000-0000-0000-0000-000000000102")
INACTIVE_ID = UUID("00000000-0000-0000-0000-000000000103")


def create_asset(
    *,
    asset_id: UUID,
    symbol: str,
    active: bool = True,
) -> Asset:
    return Asset.objects.create(
        id=asset_id,
        symbol=symbol,
        name=f"{symbol} Security",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
        is_active=active,
    )


@pytest.mark.django_db
def test_django_resolver_preserves_order_identity_and_provider_symbols() -> None:
    aapl = create_asset(asset_id=AAPL_ID, symbol="AAPL")
    brkb = create_asset(asset_id=BRKB_ID, symbol="BRK.B")
    inactive = create_asset(
        asset_id=INACTIVE_ID,
        symbol="INACTIVE",
        active=False,
    )
    AssetProviderSymbol.objects.bulk_create(
        (
            AssetProviderSymbol(
                asset=aapl,
                provider="yfinance",
                provider_symbol="AAPL",
            ),
            AssetProviderSymbol(
                asset=brkb,
                provider="yfinance",
                provider_symbol="BRK-B",
            ),
            AssetProviderSymbol(
                asset=inactive,
                provider="yfinance",
                provider_symbol="INACTIVE",
            ),
            AssetProviderSymbol(
                asset=aapl,
                provider="mock",
                provider_symbol="MOCK-AAPL",
            ),
        )
    )
    resolver: AssetResolver = DjangoAssetResolver()

    result = resolver.resolve(
        (" brk.b ", "AAPL", "UNKNOWN", "aapl", "INACTIVE"),
        provider="YFINANCE",
    )

    assert result.provider == "yfinance"
    assert result.resolved == (
        ResolvedAssetSymbol(
            requested_symbol=CanonicalUserSymbol("BRK.B"),
            asset_id=BRKB_ID,
            canonical_symbol="BRK.B",
            provider_symbol="BRK-B",
        ),
        ResolvedAssetSymbol(
            requested_symbol=CanonicalUserSymbol("AAPL"),
            asset_id=AAPL_ID,
            canonical_symbol="AAPL",
            provider_symbol="AAPL",
        ),
    )
    assert tuple(outcome.requested_symbol.symbol for outcome in result.unresolved) == (
        "UNKNOWN",
        "INACTIVE",
    )
    assert result.provider_assets == (
        ResolvedProviderAsset(
            asset_id=BRKB_ID,
            canonical_symbol="BRK.B",
            provider_symbol="BRK-B",
        ),
        ResolvedProviderAsset(
            asset_id=AAPL_ID,
            canonical_symbol="AAPL",
            provider_symbol="AAPL",
        ),
    )


@pytest.mark.django_db
def test_django_resolver_never_uses_mapping_from_another_provider() -> None:
    aapl = create_asset(asset_id=AAPL_ID, symbol="AAPL")
    AssetProviderSymbol.objects.create(
        asset=aapl,
        provider="mock",
        provider_symbol="MOCK-AAPL",
    )

    result = DjangoAssetResolver().resolve(
        ("AAPL",),
        provider="yfinance",
    )

    assert result.resolved == ()
    assert result.unresolved == (
        UnresolvedAssetSymbol(
            requested_symbol=CanonicalUserSymbol("AAPL"),
        ),
    )


@pytest.mark.django_db
def test_ambiguous_persisted_canonical_security_is_rejected() -> None:
    first = create_asset(asset_id=AAPL_ID, symbol="AAPL")
    second = create_asset(
        asset_id=BRKB_ID,
        symbol="AAPL",
    )
    AssetProviderSymbol.objects.bulk_create(
        (
            AssetProviderSymbol(
                asset=first,
                provider="mock",
                provider_symbol="AAPL-ONE",
            ),
            AssetProviderSymbol(
                asset=second,
                provider="mock",
                provider_symbol="AAPL-TWO",
            ),
        )
    )

    with pytest.raises(AssetResolutionError) as exc_info:
        DjangoAssetResolver().resolve(
            ("AAPL",),
            provider="mock",
        )

    assert exc_info.value.code is AssetResolutionErrorCode.DUPLICATE_CATALOG_RECORD
