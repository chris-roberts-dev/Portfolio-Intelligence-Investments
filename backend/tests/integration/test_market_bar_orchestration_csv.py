"""Integration-style orchestration test using the deterministic CSV provider."""

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from apps.market_data.contracts import (
    MarketBarStatus,
    normalize_market_bar_query,
)
from apps.market_data.providers.csv import CsvMarketDataProvider
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    InMemoryAssetResolver,
)
from apps.market_data.services.market_bar_query import execute_market_bar_query

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CSV_FIXTURE_ROOT = REPOSITORY_ROOT / "sample_data" / "market_data" / "csv"

AAPL_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)


def test_csv_provider_orchestration_preserves_order_status_and_provenance() -> None:
    resolver = InMemoryAssetResolver(
        (
            AssetProviderSymbolRecord(
                asset_id=AAPL_ID,
                canonical_symbol="AAPL",
                provider="csv",
                provider_symbol="AAPL",
            ),
        )
    )
    provider = CsvMarketDataProvider(
        {
            "AAPL": CSV_FIXTURE_ROOT / "aapl_daily.csv",
        },
        retrieved_at=RETRIEVED_AT,
    )
    query = normalize_market_bar_query(
        ["UNKNOWN", "AAPL"],
        start=date(2025, 1, 3),
        end=date(2025, 1, 7),
        provider="csv",
    )

    result = execute_market_bar_query(
        query,
        resolver=resolver,
        provider=provider,
    )

    assert tuple(symbol_result.symbol for symbol_result in result.results) == (
        "UNKNOWN",
        "AAPL",
    )
    assert tuple(symbol_result.status for symbol_result in result.results) == (
        MarketBarStatus.NOT_FOUND,
        MarketBarStatus.SUCCEEDED,
    )

    assert tuple(bar.trade_date for bar in result.results[1].bars) == (
        date(2025, 1, 3),
        date(2025, 1, 6),
    )

    assert result.meta.provider == "csv"
    assert result.meta.retrieved_at == RETRIEVED_AT
    assert result.row_count == 2
