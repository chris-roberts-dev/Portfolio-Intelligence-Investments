"""Property tests for canonical asset-resolution ordering."""

import string
from uuid import UUID

from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    InMemoryAssetResolver,
    canonicalize_user_symbols,
)
from hypothesis import given
from hypothesis import strategies as st

RAW_SYMBOLS = st.lists(
    st.text(
        alphabet=string.ascii_letters,
        min_size=1,
        max_size=6,
    ),
    min_size=1,
    max_size=30,
)


@given(raw_symbols=RAW_SYMBOLS)
def test_canonicalization_preserves_first_canonical_occurrence(
    raw_symbols: list[str],
) -> None:
    decorated = [
        f" {symbol.swapcase()} " if index % 2 else symbol.lower()
        for index, symbol in enumerate(raw_symbols)
    ]

    expected: list[str] = []
    seen: set[str] = set()

    for raw_symbol in decorated:
        canonical_symbol = raw_symbol.strip().upper()

        if canonical_symbol not in seen:
            seen.add(canonical_symbol)
            expected.append(canonical_symbol)

    result = canonicalize_user_symbols(decorated)

    assert tuple(symbol.symbol for symbol in result) == tuple(expected)


@given(raw_symbols=RAW_SYMBOLS)
def test_provider_assets_preserve_resolved_first_occurrence_order(
    raw_symbols: list[str],
) -> None:
    canonical_symbols = canonicalize_user_symbols(raw_symbols)

    records = tuple(
        AssetProviderSymbolRecord(
            asset_id=UUID(int=index + 1),
            canonical_symbol=symbol.symbol,
            provider="mock",
            provider_symbol=f"MOCK-{symbol.symbol}",
        )
        for index, symbol in enumerate(canonical_symbols)
    )
    resolver = InMemoryAssetResolver(records)

    result = resolver.resolve(
        raw_symbols,
        provider="mock",
    )

    assert tuple(
        provider_asset.canonical_symbol for provider_asset in result.provider_assets
    ) == tuple(symbol.symbol for symbol in canonical_symbols)
