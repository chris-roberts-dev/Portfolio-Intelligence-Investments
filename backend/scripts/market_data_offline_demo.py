"""Deterministic offline Phase 2 market-data demonstration.

This script exercises the provider-neutral symbol-resolution and orchestration
contracts using only committed CSV sample data. It performs no network I/O.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from apps.market_data.contracts import MarketBarStatus, normalize_market_bar_query
from apps.market_data.providers.csv import CsvMarketDataProvider
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    InMemoryAssetResolver,
)
from apps.market_data.services.market_bar_query import execute_market_bar_query

SAMPLE_DATA_DIR = Path(__file__).resolve().parents[1] / "sample_data" / "market_data"
RETRIEVED_AT = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)

AAPL_ID = UUID("00000000-0000-0000-0000-000000000101")
MSFT_ID = UUID("00000000-0000-0000-0000-000000000102")
EMPTY_ID = UUID("00000000-0000-0000-0000-000000000103")

EXPECTED_SYMBOLS = ("AAPL", "MSFT", "EMPTY", "UNKNOWN")
EXPECTED_STATUSES = (
    MarketBarStatus.SUCCEEDED,
    MarketBarStatus.SUCCEEDED,
    MarketBarStatus.NO_DATA,
    MarketBarStatus.NOT_FOUND,
)


def build_offline_demo_result():
    """Run the deterministic CSV-backed multi-symbol market-data workflow."""
    query = normalize_market_bar_query(
        ["AAPL", "MSFT", "EMPTY", "UNKNOWN", "AAPL"],
        start=date(2025, 1, 2),
        end=date(2025, 1, 9),
        interval="1d",
        provider="csv",
    )
    resolver = InMemoryAssetResolver(
        (
            AssetProviderSymbolRecord(
                asset_id=AAPL_ID,
                canonical_symbol="AAPL",
                provider="csv",
                provider_symbol="AAPL",
            ),
            AssetProviderSymbolRecord(
                asset_id=MSFT_ID,
                canonical_symbol="MSFT",
                provider="csv",
                provider_symbol="MSFT",
            ),
            AssetProviderSymbolRecord(
                asset_id=EMPTY_ID,
                canonical_symbol="EMPTY",
                provider="csv",
                provider_symbol="EMPTY",
            ),
        )
    )
    provider = CsvMarketDataProvider(
        {
            "AAPL": SAMPLE_DATA_DIR / "aapl.csv",
            "MSFT": SAMPLE_DATA_DIR / "msft.csv",
            "EMPTY": SAMPLE_DATA_DIR / "empty.csv",
        },
        retrieved_at=RETRIEVED_AT,
    )

    return execute_market_bar_query(
        query,
        resolver=resolver,
        provider=provider,
    )


def validate_offline_demo_result(result) -> None:
    """Fail loudly if the offline demonstration no longer proves the Data Gate."""
    symbols = tuple(item.symbol for item in result.results)
    statuses = tuple(item.status for item in result.results)

    if symbols != EXPECTED_SYMBOLS:
        raise RuntimeError(
            f"Unexpected result order: expected {EXPECTED_SYMBOLS!r}, got {symbols!r}."
        )

    if statuses != EXPECTED_STATUSES:
        raise RuntimeError(
            f"Unexpected statuses: expected {EXPECTED_STATUSES!r}, got {statuses!r}."
        )

    if result.meta.provider != "csv":
        raise RuntimeError(f"Unexpected provider provenance: {result.meta.provider!r}.")

    if result.meta.retrieved_at != RETRIEVED_AT:
        raise RuntimeError("Unexpected retrieval timestamp provenance.")

    succeeded = [item for item in result.results if item.status is MarketBarStatus.SUCCEEDED]

    if any(len(item.bars) != 5 for item in succeeded):
        raise RuntimeError("Expected five daily bars for each successful sample symbol.")

    for item in succeeded:
        if any(bar.source != "csv" for bar in item.bars):
            raise RuntimeError("Successful sample bars must retain csv source provenance.")


def serialize_summary(result) -> dict[str, object]:
    """Return a stable human-readable summary without presentation calculations."""
    return {
        "provider": result.meta.provider,
        "retrieved_at": result.meta.retrieved_at.isoformat(),
        "start": result.meta.start.isoformat(),
        "end": result.meta.end.isoformat(),
        "interval": result.meta.interval.value,
        "results": [
            {
                "symbol": item.symbol,
                "status": item.status.value,
                "bar_count": len(item.bars),
                "warnings": list(item.warnings),
            }
            for item in result.results
        ],
        "row_count": result.row_count,
    }


def main() -> int:
    result = build_offline_demo_result()
    validate_offline_demo_result(result)
    print(json.dumps(serialize_summary(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
