"""Unit tests for explicit DRF market-bar serializer contracts."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from apps.market_data.api.serializers import (
    MarketBarBatchResultSerializer,
    MarketBarQuerySerializer,
)
from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    MarketBarStatus,
    MarketBarSymbolResult,
)
from portfolio_engine.config import (
    MAX_BAR_QUERY_CALENDAR_DAYS,
    MAX_BAR_QUERY_SYMBOLS,
)
from portfolio_engine.contracts.market_data import PriceBar

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)


def test_valid_request_delegates_normalization_to_application_contract() -> None:
    serializer = MarketBarQuerySerializer(
        data={
            "symbols": [" msft ", "AAPL", "MSFT"],
            "start": "2026-01-01",
            "end": "2026-01-05",
            "interval": "1d",
            "provider": " YFinance ",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["symbols"] == ["MSFT", "AAPL"]
    assert serializer.validated_data["provider"] == "yfinance"
    assert serializer.normalized_query.symbols == ("MSFT", "AAPL")
    assert serializer.normalized_query.provider == "yfinance"
    assert serializer.normalized_query.start == date(2026, 1, 1)
    assert serializer.normalized_query.end == date(2026, 1, 5)


def test_request_serializer_surfaces_symbol_bound_failure() -> None:
    serializer = MarketBarQuerySerializer(
        data={
            "symbols": [f"SYM{index}" for index in range(MAX_BAR_QUERY_SYMBOLS + 1)],
            "start": "2026-01-01",
            "end": "2026-01-05",
        }
    )

    assert not serializer.is_valid()
    assert "symbols" in serializer.errors


def test_request_serializer_surfaces_history_bound_failure() -> None:
    start = date(2000, 1, 1)
    end = start + timedelta(days=MAX_BAR_QUERY_CALENDAR_DAYS + 1)
    serializer = MarketBarQuerySerializer(
        data={
            "symbols": ["AAPL"],
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
    )

    assert not serializer.is_valid()
    assert "end" in serializer.errors


def test_request_serializer_surfaces_invalid_date_range() -> None:
    serializer = MarketBarQuerySerializer(
        data={
            "symbols": ["AAPL"],
            "start": "2026-01-05",
            "end": "2026-01-05",
        }
    )

    assert not serializer.is_valid()
    assert "end" in serializer.errors


def test_batch_response_preserves_statuses_raw_numbers_and_provenance() -> None:
    bar = PriceBar(
        asset_id=ASSET_ID,
        trade_date=date(2026, 1, 2),
        open=100.125,
        high=103.25,
        low=99.5,
        close=102.75,
        adjusted_close=101.875,
        volume=1_234_567,
        source="mock",
        retrieved_at=RETRIEVED_AT,
    )
    batch = MarketBarBatchResult(
        results=(
            MarketBarSymbolResult(
                symbol="AAPL",
                asset_id=ASSET_ID,
                status=MarketBarStatus.SUCCEEDED,
                bars=(bar,),
            ),
            MarketBarSymbolResult(
                symbol="UNKNOWN",
                asset_id=None,
                status=MarketBarStatus.NOT_FOUND,
            ),
            MarketBarSymbolResult(
                symbol="EMPTY",
                asset_id=ASSET_ID,
                status=MarketBarStatus.NO_DATA,
                warnings=("No bars were returned.",),
            ),
            MarketBarSymbolResult(
                symbol="FAILED",
                asset_id=ASSET_ID,
                status=MarketBarStatus.FAILED,
                warnings=("Provider failed.",),
            ),
        ),
        meta=MarketBarBatchMeta(
            provider="mock",
            retrieved_at=RETRIEVED_AT,
            interval=MarketBarInterval.DAILY,
            start=date(2026, 1, 1),
            end=date(2026, 1, 5),
        ),
    )

    data = MarketBarBatchResultSerializer(batch).data

    assert [result["status"] for result in data["results"]] == [
        "SUCCEEDED",
        "NOT_FOUND",
        "NO_DATA",
        "FAILED",
    ]

    serialized_bar = data["results"][0]["bars"][0]

    assert serialized_bar["open"] == 100.125
    assert serialized_bar["adjusted_close"] == 101.875
    assert serialized_bar["volume"] == 1_234_567
    assert isinstance(serialized_bar["open"], float)

    assert data["results"][2]["warnings"] == ["No bars were returned."]
    assert data["results"][3]["warnings"] == ["Provider failed."]
    assert data["meta"]["provider"] == "mock"
    assert data["meta"]["interval"] == "1d"
    assert data["meta"]["start"] == "2026-01-01"
    assert data["meta"]["end"] == "2026-01-05"
    assert data["row_count"] == 1
