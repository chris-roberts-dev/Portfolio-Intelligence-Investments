"""Unit tests for provider-neutral asset/provider-symbol resolution."""

from uuid import UUID

import pytest
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    AssetResolutionError,
    AssetResolutionErrorCode,
    AssetResolver,
    CanonicalUserSymbol,
    InMemoryAssetResolver,
    ResolvedAssetSymbol,
    UnresolvedAssetReason,
    UnresolvedAssetSymbol,
    canonicalize_user_symbols,
)

from apps.market_data.providers.base import ResolvedProviderAsset

AAPL_ID = UUID("00000000-0000-0000-0000-000000000001")
MSFT_ID = UUID("00000000-0000-0000-0000-000000000002")
BRKB_ID = UUID("00000000-0000-0000-0000-000000000003")

RECORDS = (
    AssetProviderSymbolRecord(
        asset_id=AAPL_ID,
        canonical_symbol="AAPL",
        provider="mock",
        provider_symbol="AAPL",
    ),
    AssetProviderSymbolRecord(
        asset_id=MSFT_ID,
        canonical_symbol="MSFT",
        provider="mock",
        provider_symbol="MSFT",
    ),
    AssetProviderSymbolRecord(
        asset_id=BRKB_ID,
        canonical_symbol="BRK.B",
        provider="mock",
        provider_symbol="BRK-B",
    ),
    AssetProviderSymbolRecord(
        asset_id=AAPL_ID,
        canonical_symbol="AAPL",
        provider="other",
        provider_symbol="AAPL.OTHER",
    ),
)


def test_symbol_canonicalization_preserves_first_occurrence_order() -> None:
    symbols = canonicalize_user_symbols([" msft ", "AAPL", "MSFT", " brk.b ", "aapl"])

    assert symbols == (
        CanonicalUserSymbol("MSFT"),
        CanonicalUserSymbol("AAPL"),
        CanonicalUserSymbol("BRK.B"),
    )


def test_resolver_maps_symbols_to_internal_uuid_identity() -> None:
    resolver = InMemoryAssetResolver(RECORDS)

    result = resolver.resolve(
        ["AAPL", "MSFT"],
        provider="mock",
    )

    assert result.resolved == (
        ResolvedAssetSymbol(
            requested_symbol=CanonicalUserSymbol("AAPL"),
            asset_id=AAPL_ID,
            canonical_symbol="AAPL",
            provider_symbol="AAPL",
        ),
        ResolvedAssetSymbol(
            requested_symbol=CanonicalUserSymbol("MSFT"),
            asset_id=MSFT_ID,
            canonical_symbol="MSFT",
            provider_symbol="MSFT",
        ),
    )


def test_resolver_uses_provider_specific_symbol_without_rewriting_security() -> None:
    resolver = InMemoryAssetResolver(RECORDS)

    mock_result = resolver.resolve(
        ["AAPL", "BRK.B"],
        provider="mock",
    )
    other_result = resolver.resolve(
        ["AAPL"],
        provider="other",
    )

    assert mock_result.resolved[0].canonical_symbol == "AAPL"
    assert mock_result.resolved[0].provider_symbol == "AAPL"

    assert mock_result.resolved[1].canonical_symbol == "BRK.B"
    assert mock_result.resolved[1].provider_symbol == "BRK-B"

    assert other_result.resolved[0].canonical_symbol == "AAPL"
    assert other_result.resolved[0].provider_symbol == "AAPL.OTHER"


def test_unresolved_symbol_is_preserved_in_request_order() -> None:
    resolver = InMemoryAssetResolver(RECORDS)

    result = resolver.resolve(
        ["MSFT", "UNKNOWN", "AAPL", "msft"],
        provider="mock",
    )

    assert tuple(outcome.requested_symbol.symbol for outcome in result.outcomes) == (
        "MSFT",
        "UNKNOWN",
        "AAPL",
    )

    assert result.unresolved == (
        UnresolvedAssetSymbol(
            requested_symbol=CanonicalUserSymbol("UNKNOWN"),
            reason=UnresolvedAssetReason.NOT_FOUND,
        ),
    )


def test_provider_assets_contain_only_resolved_assets_in_request_order() -> None:
    resolver = InMemoryAssetResolver(RECORDS)

    result = resolver.resolve(
        ["UNKNOWN", "MSFT", "AAPL"],
        provider="mock",
    )

    assert result.provider_assets == (
        ResolvedProviderAsset(
            asset_id=MSFT_ID,
            canonical_symbol="MSFT",
            provider_symbol="MSFT",
        ),
        ResolvedProviderAsset(
            asset_id=AAPL_ID,
            canonical_symbol="AAPL",
            provider_symbol="AAPL",
        ),
    )


def test_missing_symbol_is_not_rewritten_to_another_catalog_security() -> None:
    resolver = InMemoryAssetResolver(
        (
            AssetProviderSymbolRecord(
                asset_id=MSFT_ID,
                canonical_symbol="MSFT",
                provider="mock",
                provider_symbol="MSFT",
            ),
        )
    )

    result = resolver.resolve(
        ["AAPL"],
        provider="mock",
    )

    assert result.resolved == ()
    assert result.unresolved[0].requested_symbol.symbol == "AAPL"


def test_provider_without_symbol_mapping_produces_unresolved_outcome() -> None:
    resolver = InMemoryAssetResolver(RECORDS)

    result = resolver.resolve(
        ["BRK.B"],
        provider="other",
    )

    assert result.resolved == ()
    assert result.unresolved[0].requested_symbol.symbol == "BRK.B"


def test_duplicate_catalog_key_is_rejected() -> None:
    duplicate_records = (
        AssetProviderSymbolRecord(
            asset_id=AAPL_ID,
            canonical_symbol="AAPL",
            provider="mock",
            provider_symbol="AAPL",
        ),
        AssetProviderSymbolRecord(
            asset_id=MSFT_ID,
            canonical_symbol="AAPL",
            provider="mock",
            provider_symbol="AAPL-OTHER",
        ),
    )

    with pytest.raises(AssetResolutionError) as exc_info:
        InMemoryAssetResolver(duplicate_records)

    assert exc_info.value.code is AssetResolutionErrorCode.DUPLICATE_CATALOG_RECORD


def test_blank_user_symbol_is_rejected() -> None:
    with pytest.raises(AssetResolutionError) as exc_info:
        canonicalize_user_symbols(["AAPL", "   "])

    assert exc_info.value.code is AssetResolutionErrorCode.BLANK_SYMBOL


def test_blank_provider_is_rejected() -> None:
    resolver = InMemoryAssetResolver(RECORDS)

    with pytest.raises(AssetResolutionError) as exc_info:
        resolver.resolve(["AAPL"], provider="   ")

    assert exc_info.value.code is AssetResolutionErrorCode.BLANK_PROVIDER


def test_in_memory_resolver_satisfies_asset_resolver_protocol() -> None:
    resolver: AssetResolver = InMemoryAssetResolver(RECORDS)

    assert isinstance(resolver, AssetResolver)
