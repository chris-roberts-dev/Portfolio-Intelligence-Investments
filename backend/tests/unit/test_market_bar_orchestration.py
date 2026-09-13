"""Unit tests for provider-batch to application-result orchestration."""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from apps.market_data.contracts import (
    MarketBarStatus,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import (
    MarketDataProvider,
    ProviderBatchResult,
    ProviderIssue,
    ResolvedProviderAsset,
)
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.services.asset_resolution import (
    AssetProviderSymbolRecord,
    InMemoryAssetResolver,
)
from apps.market_data.services.market_bar_query import (
    MarketBarOrchestrationError,
    MarketBarOrchestrationErrorCode,
    execute_market_bar_query,
)
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame

AAPL_ID = UUID("00000000-0000-0000-0000-000000000001")
EMPTY_ID = UUID("00000000-0000-0000-0000-000000000002")
NO_DATA_ID = UUID("00000000-0000-0000-0000-000000000003")
FAILED_ID = UUID("00000000-0000-0000-0000-000000000004")
QUALITY_ID = UUID("00000000-0000-0000-0000-000000000005")

RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)

RESOLVER = InMemoryAssetResolver(
    (
        AssetProviderSymbolRecord(
            asset_id=AAPL_ID,
            canonical_symbol="AAPL",
            provider="mock",
            provider_symbol="AAPL",
        ),
        AssetProviderSymbolRecord(
            asset_id=EMPTY_ID,
            canonical_symbol="EMPTY",
            provider="mock",
            provider_symbol="EMPTY",
        ),
        AssetProviderSymbolRecord(
            asset_id=NO_DATA_ID,
            canonical_symbol="NODATA",
            provider="mock",
            provider_symbol="NODATA",
        ),
        AssetProviderSymbolRecord(
            asset_id=FAILED_ID,
            canonical_symbol="FAIL",
            provider="mock",
            provider_symbol="FAIL",
        ),
        AssetProviderSymbolRecord(
            asset_id=QUALITY_ID,
            canonical_symbol="QUALITY",
            provider="mock",
            provider_symbol="QUALITY",
        ),
    )
)


class RecordingProvider:
    """Protocol-compatible wrapper recording provider-call asset arguments."""

    def __init__(self, delegate: MarketDataProvider) -> None:
        self._delegate = delegate
        self.calls: list[tuple[ResolvedProviderAsset, ...]] = []

    @property
    def name(self) -> str:
        return self._delegate.name

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        self.calls.append(tuple(assets))
        return self._delegate.get_daily_bars(assets, start, end)


def make_frame(
    asset_id: UUID,
    *trade_dates: date,
) -> PriceFrame:
    """Return a valid deterministic mock frame."""
    return tuple(
        PriceBar(
            asset_id=asset_id,
            trade_date=trade_date,
            open=100.0,
            high=103.0,
            low=99.0,
            close=102.0,
            adjusted_close=101.5,
            volume=1_000_000,
            source="mock",
            retrieved_at=RETRIEVED_AT,
        )
        for trade_date in trade_dates
    )


def test_orchestration_preserves_order_and_maps_mixed_provider_outcomes() -> None:
    provider = RecordingProvider(
        MockMarketDataProvider(
            {
                AAPL_ID: make_frame(AAPL_ID, date(2026, 1, 2)),
                EMPTY_ID: (),
            },
            retrieved_at=RETRIEVED_AT,
            issues={
                NO_DATA_ID: ProviderIssue(
                    code="NO_DATA",
                    message="No provider bars exist for this period.",
                ),
                FAILED_ID: ProviderIssue(
                    code="FAILED",
                    message="Configured deterministic provider failure.",
                ),
                QUALITY_ID: ProviderIssue(
                    code="DATA_QUALITY_ERROR",
                    message="Configured deterministic quality failure.",
                ),
            },
        )
    )
    query = normalize_market_bar_query(
        [
            "UNKNOWN",
            "AAPL",
            "EMPTY",
            "NODATA",
            "FAIL",
            "QUALITY",
        ],
        start=date(2026, 1, 1),
        end=date(2026, 1, 4),
        provider="mock",
    )

    result = execute_market_bar_query(
        query,
        resolver=RESOLVER,
        provider=provider,
    )

    assert tuple(symbol_result.symbol for symbol_result in result.results) == (
        "UNKNOWN",
        "AAPL",
        "EMPTY",
        "NODATA",
        "FAIL",
        "QUALITY",
    )
    assert tuple(symbol_result.status for symbol_result in result.results) == (
        MarketBarStatus.NOT_FOUND,
        MarketBarStatus.SUCCEEDED,
        MarketBarStatus.NO_DATA,
        MarketBarStatus.NO_DATA,
        MarketBarStatus.FAILED,
        MarketBarStatus.FAILED,
    )

    assert len(provider.calls) == 1
    assert tuple(asset.canonical_symbol for asset in provider.calls[0]) == (
        "AAPL",
        "EMPTY",
        "NODATA",
        "FAIL",
        "QUALITY",
    )

    assert result.results[0].asset_id is None
    assert result.results[1].asset_id == AAPL_ID
    assert result.results[1].bars == make_frame(
        AAPL_ID,
        date(2026, 1, 2),
    )
    assert result.results[2].bars == ()
    assert result.results[3].warnings == ("No provider bars exist for this period.",)
    assert result.results[4].warnings == ("Configured deterministic provider failure.",)
    assert result.results[5].warnings == ("Configured deterministic quality failure.",)

    assert result.meta.provider == "mock"
    assert result.meta.retrieved_at == RETRIEVED_AT
    assert result.meta.start == date(2026, 1, 1)
    assert result.meta.end == date(2026, 1, 4)


def test_orchestration_enforces_actual_output_row_limit() -> None:
    provider = MockMarketDataProvider(
        {
            AAPL_ID: make_frame(
                AAPL_ID,
                date(2026, 1, 2),
                date(2026, 1, 3),
            )
        },
        retrieved_at=RETRIEVED_AT,
    )
    query = normalize_market_bar_query(
        ["AAPL"],
        start=date(2026, 1, 1),
        end=date(2026, 1, 4),
        provider="mock",
    )

    with pytest.raises(MarketBarOrchestrationError) as exc_info:
        execute_market_bar_query(
            query,
            resolver=RESOLVER,
            provider=provider,
            max_rows=1,
        )

    assert exc_info.value.code is MarketBarOrchestrationErrorCode.ACTUAL_ROW_LIMIT_EXCEEDED
    assert exc_info.value.actual_rows == 2
    assert exc_info.value.max_rows == 1
