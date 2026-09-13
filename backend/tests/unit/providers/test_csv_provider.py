"""Focused tests for the deterministic CSV provider."""

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from apps.market_data.providers.base import ResolvedProviderAsset
from apps.market_data.providers.csv import (
    CSV_BAR_COLUMNS,
    CsvMarketDataProvider,
    CsvProviderIssueCode,
)
from portfolio_engine.contracts.market_data_validation import validate_price_frame

REPO_ROOT = Path(__file__).resolve().parents[4]
CSV_FIXTURE_ROOT = REPO_ROOT / "sample_data" / "market_data" / "csv"

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)
ASSET = ResolvedProviderAsset(
    asset_id=ASSET_ID,
    canonical_symbol="AAPL",
    provider_symbol="AAPL",
)


def test_csv_schema_is_explicit_and_minimal() -> None:
    assert CSV_BAR_COLUMNS == (
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "adjusted_close",
        "volume",
    )


def test_committed_valid_fixture_normalizes_to_canonical_frame() -> None:
    provider = CsvMarketDataProvider(
        {
            "AAPL": CSV_FIXTURE_ROOT / "aapl_daily.csv",
        },
        retrieved_at=RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (ASSET,),
        date(2025, 1, 3),
        date(2025, 1, 7),
    )

    frame = result.frames[ASSET_ID]

    assert validate_price_frame(frame) is frame
    assert tuple(bar.trade_date for bar in frame) == (
        date(2025, 1, 3),
        date(2025, 1, 6),
    )
    assert all(bar.asset_id == ASSET_ID for bar in frame)
    assert all(bar.source == "csv" for bar in frame)
    assert all(bar.retrieved_at == RETRIEVED_AT for bar in frame)
    assert result.issues == {}


def test_missing_provider_symbol_path_returns_no_data() -> None:
    provider = CsvMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (ASSET,),
        date(2025, 1, 1),
        date(2025, 1, 10),
    )

    assert ASSET_ID not in result.frames
    assert result.issues[ASSET_ID].code == CsvProviderIssueCode.NO_DATA


def test_invalid_committed_fixture_returns_data_quality_issue() -> None:
    provider = CsvMarketDataProvider(
        {
            "AAPL": CSV_FIXTURE_ROOT / "invalid_non_positive_price.csv",
        },
        retrieved_at=RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (ASSET,),
        date(2025, 1, 1),
        date(2025, 1, 10),
    )

    assert ASSET_ID not in result.frames
    assert result.issues[ASSET_ID].code == CsvProviderIssueCode.DATA_QUALITY_ERROR


def test_missing_local_file_returns_csv_error(
    tmp_path: Path,
) -> None:
    provider = CsvMarketDataProvider(
        {
            "AAPL": tmp_path / "missing.csv",
        },
        retrieved_at=RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (ASSET,),
        date(2025, 1, 1),
        date(2025, 1, 10),
    )

    assert ASSET_ID not in result.frames
    assert result.issues[ASSET_ID].code == CsvProviderIssueCode.CSV_ERROR
