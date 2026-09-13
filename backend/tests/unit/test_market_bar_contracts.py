"""Unit tests for application-level market-bar contracts."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest

from apps.market_data.contracts import (
    DEFAULT_MARKET_BAR_QUERY_LIMITS,
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    MarketBarQueryError,
    MarketBarQueryErrorCode,
    MarketBarQueryLimits,
    MarketBarStatus,
    MarketBarSymbolResult,
    normalize_market_bar_query,
)
from portfolio_engine.config import (
    MAX_BAR_QUERY_CALENDAR_DAYS,
    MAX_BAR_QUERY_ROWS,
    MAX_BAR_QUERY_SYMBOLS,
)
from portfolio_engine.contracts.market_data import PriceBar

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 3, 12, tzinfo=UTC)


def assert_query_error(
    expected_code: MarketBarQueryErrorCode,
    *,
    symbols: Sequence[str],
    start: date,
    end: date,
    interval: str | MarketBarInterval = MarketBarInterval.DAILY,
    provider: str | None = None,
    limits: MarketBarQueryLimits = DEFAULT_MARKET_BAR_QUERY_LIMITS,
) -> MarketBarQueryError:
    """Execute a query normalization expected to fail with one stable code."""
    with pytest.raises(MarketBarQueryError) as exc_info:
        normalize_market_bar_query(
            symbols,
            start=start,
            end=end,
            interval=interval,
            provider=provider,
            limits=limits,
        )

    assert exc_info.value.code is expected_code
    return exc_info.value


def make_bar() -> PriceBar:
    """Return one valid deterministic canonical price bar."""
    return PriceBar(
        asset_id=ASSET_ID,
        trade_date=date(2025, 1, 2),
        open=100.0,
        high=103.0,
        low=99.0,
        close=102.0,
        adjusted_close=101.5,
        volume=1_000_000,
        source="mock",
        retrieved_at=RETRIEVED_AT,
    )


def test_normative_market_bar_query_limits_are_centralized() -> None:
    assert MAX_BAR_QUERY_SYMBOLS == 50
    assert MAX_BAR_QUERY_CALENDAR_DAYS == 7305
    assert MAX_BAR_QUERY_ROWS == 500_000


def test_symbol_normalization_preserves_first_occurrence_order() -> None:
    query = normalize_market_bar_query(
        [" msft ", "AAPL", "MSFT", " vti ", "aapl"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 10),
        provider=" YFinance ",
    )

    assert query.symbols == ("MSFT", "AAPL", "VTI")
    assert query.provider == "yfinance"
    assert query.interval is MarketBarInterval.DAILY
    assert query.calendar_days == 9
    assert query.estimated_max_rows == 27


def test_empty_symbol_list_is_rejected() -> None:
    assert_query_error(
        MarketBarQueryErrorCode.EMPTY_SYMBOLS,
        symbols=[],
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
    )


def test_blank_symbol_is_rejected() -> None:
    error = assert_query_error(
        MarketBarQueryErrorCode.EMPTY_SYMBOL,
        symbols=["AAPL", "  "],
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
    )

    assert error.field == "symbols"


def test_raw_symbol_count_limit_applies_before_deduplication() -> None:
    assert_query_error(
        MarketBarQueryErrorCode.TOO_MANY_SYMBOLS,
        symbols=["AAPL"] * (MAX_BAR_QUERY_SYMBOLS + 1),
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
    )


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(2025, 1, 1), date(2025, 1, 1)),
        (date(2025, 1, 2), date(2025, 1, 1)),
    ],
)
def test_invalid_date_range_is_rejected(start: date, end: date) -> None:
    assert_query_error(
        MarketBarQueryErrorCode.INVALID_DATE_RANGE,
        symbols=["AAPL"],
        start=start,
        end=end,
    )


def test_history_limit_is_enforced() -> None:
    start = date(2000, 1, 1)

    assert_query_error(
        MarketBarQueryErrorCode.HISTORY_LIMIT_EXCEEDED,
        symbols=["AAPL"],
        start=start,
        end=start + timedelta(days=MAX_BAR_QUERY_CALENDAR_DAYS + 1),
    )


def test_row_limit_is_enforced() -> None:
    limits = MarketBarQueryLimits(
        max_symbols=10,
        max_calendar_days=10,
        max_rows=3,
    )

    assert_query_error(
        MarketBarQueryErrorCode.ROW_LIMIT_EXCEEDED,
        symbols=["AAPL", "MSFT"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 3),
        limits=limits,
    )


def test_unsupported_interval_is_rejected() -> None:
    assert_query_error(
        MarketBarQueryErrorCode.UNSUPPORTED_INTERVAL,
        symbols=["AAPL"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
        interval="1h",
    )


def test_blank_provider_is_rejected_when_supplied() -> None:
    error = assert_query_error(
        MarketBarQueryErrorCode.INVALID_PROVIDER,
        symbols=["AAPL"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 2),
        provider="   ",
    )

    assert error.field == "provider"


def test_per_symbol_status_values_match_canonical_contract() -> None:
    assert {status.value for status in MarketBarStatus} == {
        "SUCCEEDED",
        "NOT_FOUND",
        "NO_DATA",
        "FAILED",
    }


def test_succeeded_result_requires_asset_and_bars() -> None:
    result = MarketBarSymbolResult(
        symbol="AAPL",
        asset_id=ASSET_ID,
        status=MarketBarStatus.SUCCEEDED,
        bars=(make_bar(),),
    )

    assert result.asset_id == ASSET_ID
    assert len(result.bars) == 1


def test_succeeded_result_rejects_missing_asset() -> None:
    with pytest.raises(ValueError, match="asset_id"):
        MarketBarSymbolResult(
            symbol="AAPL",
            asset_id=None,
            status=MarketBarStatus.SUCCEEDED,
            bars=(make_bar(),),
        )


def test_no_data_requires_resolved_asset_and_no_bars() -> None:
    result = MarketBarSymbolResult(
        symbol="AAPL",
        asset_id=ASSET_ID,
        status=MarketBarStatus.NO_DATA,
    )

    assert result.asset_id == ASSET_ID
    assert result.bars == ()


def test_non_success_result_rejects_bars() -> None:
    with pytest.raises(ValueError, match="Only SUCCEEDED"):
        MarketBarSymbolResult(
            symbol="AAPL",
            asset_id=ASSET_ID,
            status=MarketBarStatus.FAILED,
            bars=(make_bar(),),
        )


def test_batch_result_retains_provenance_and_row_count() -> None:
    result = MarketBarSymbolResult(
        symbol="AAPL",
        asset_id=ASSET_ID,
        status=MarketBarStatus.SUCCEEDED,
        bars=(make_bar(),),
        warnings=("fixture warning",),
    )
    meta = MarketBarBatchMeta(
        provider="mock",
        retrieved_at=RETRIEVED_AT,
        interval=MarketBarInterval.DAILY,
        start=date(2025, 1, 1),
        end=date(2025, 1, 3),
    )
    batch = MarketBarBatchResult(results=(result,), meta=meta)

    assert batch.results[0].symbol == "AAPL"
    assert batch.meta.provider == "mock"
    assert batch.row_count == 1
