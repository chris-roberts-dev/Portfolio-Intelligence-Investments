"""Property tests for application-level market-bar request normalization."""

import string
from datetime import date

from hypothesis import given
from hypothesis import strategies as st

from apps.market_data.contracts import normalize_market_bar_query
from portfolio_engine.config import MAX_BAR_QUERY_SYMBOLS

SYMBOL_TEXT = st.text(
    alphabet=string.ascii_letters,
    min_size=1,
    max_size=6,
)

RAW_SYMBOL_LISTS = st.lists(
    SYMBOL_TEXT,
    min_size=1,
    max_size=MAX_BAR_QUERY_SYMBOLS,
)


@given(raw_symbols=RAW_SYMBOL_LISTS)
def test_symbol_normalization_preserves_first_canonical_occurrence(
    raw_symbols: list[str],
) -> None:
    decorated_symbols = [
        f"  {symbol.swapcase()}  " if index % 2 else symbol.lower()
        for index, symbol in enumerate(raw_symbols)
    ]

    expected: list[str] = []
    seen: set[str] = set()

    for symbol in decorated_symbols:
        canonical_symbol = symbol.strip().upper()

        if canonical_symbol not in seen:
            seen.add(canonical_symbol)
            expected.append(canonical_symbol)

    query = normalize_market_bar_query(
        decorated_symbols,
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
    )

    assert query.symbols == tuple(expected)


@given(
    duplicates=st.integers(
        min_value=1,
        max_value=MAX_BAR_QUERY_SYMBOLS,
    )
)
def test_deduplication_never_reorders_first_symbol(duplicates: int) -> None:
    raw_symbols = [" msft "] * duplicates

    query = normalize_market_bar_query(
        raw_symbols,
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
    )

    assert query.symbols == ("MSFT",)
