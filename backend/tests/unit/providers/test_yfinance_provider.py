"""Focused deterministic tests for the yfinance provider adapter."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast
from uuid import UUID

import pandas as pd

from apps.market_data.providers.base import ResolvedProviderAsset
from apps.market_data.providers.yfinance import (
    YFinanceMarketDataProvider,
    YFinanceProviderIssueCode,
)

AAPL_ID = UUID("00000000-0000-0000-0000-000000000001")
MSFT_ID = UUID("00000000-0000-0000-0000-000000000002")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)

AAPL = ResolvedProviderAsset(
    asset_id=AAPL_ID,
    canonical_symbol="AAPL",
    provider_symbol="AAPL",
)
MSFT = ResolvedProviderAsset(
    asset_id=MSFT_ID,
    canonical_symbol="MSFT",
    provider_symbol="MSFT",
)


def make_raw_frame(
    symbol: str,
    *,
    open_price: float = 100.0,
) -> pd.DataFrame:
    symbol_frame = pd.DataFrame(
        {
            "Open": [open_price, 101.0],
            "High": [103.0, 104.0],
            "Low": [99.0, 100.0],
            "Close": [102.0, 103.0],
            "Adj Close": [101.5, 102.5],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.DatetimeIndex(
            [date(2026, 1, 2), date(2026, 1, 3)],
            name="Date",
        ),
    )

    return pd.concat({symbol: symbol_frame}, axis=1)


def test_yfinance_batches_symbols_and_requests_raw_daily_prices() -> None:
    captured_kwargs: dict[str, object] = {}

    def downloader(**kwargs: object) -> pd.DataFrame:
        captured_kwargs.update(kwargs)
        return pd.concat(
            {
                "AAPL": make_raw_frame("AAPL")["AAPL"],
                "MSFT": make_raw_frame("MSFT")["MSFT"],
            },
            axis=1,
        )

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (AAPL, MSFT),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )

    assert cast(list[str], captured_kwargs["tickers"]) == ["AAPL", "MSFT"]
    assert captured_kwargs["start"] == "2026-01-01"
    assert captured_kwargs["end"] == "2026-01-04"
    assert captured_kwargs["interval"] == "1d"
    assert captured_kwargs["auto_adjust"] is False
    assert captured_kwargs["repair"] is False
    assert captured_kwargs["group_by"] == "ticker"
    assert captured_kwargs["multi_level_index"] is True

    assert tuple(result.frames) == (AAPL_ID, MSFT_ID)
    assert result.issues == {}
    assert result.retrieved_at == RETRIEVED_AT

    assert all(
        bar.asset_id == AAPL_ID and bar.source == "yfinance" and bar.retrieved_at == RETRIEVED_AT
        for bar in result.frames[AAPL_ID]
    )


def test_yfinance_provider_exception_maps_to_explicit_asset_issues() -> None:
    def downloader(**_kwargs: object) -> pd.DataFrame:
        raise RuntimeError("configured provider failure")

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (AAPL, MSFT),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )

    assert result.frames == {}
    assert result.issues[AAPL_ID].code == YFinanceProviderIssueCode.PROVIDER_ERROR
    assert result.issues[MSFT_ID].code == YFinanceProviderIssueCode.PROVIDER_ERROR


def test_missing_symbol_history_maps_to_no_data_without_fallback() -> None:
    def downloader(**_kwargs: object) -> pd.DataFrame:
        return make_raw_frame("AAPL")

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (AAPL, MSFT),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )

    assert AAPL_ID in result.frames
    assert MSFT_ID not in result.frames
    assert result.issues[MSFT_ID].code == YFinanceProviderIssueCode.NO_DATA


def test_invalid_normalized_prices_map_to_data_quality_issue() -> None:
    def downloader(**_kwargs: object) -> pd.DataFrame:
        return make_raw_frame(
            "AAPL",
            open_price=0.0,
        )

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (AAPL,),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )

    assert AAPL_ID not in result.frames
    assert result.issues[AAPL_ID].code == YFinanceProviderIssueCode.DATA_QUALITY_ERROR


def test_missing_required_yfinance_column_maps_to_normalization_issue() -> None:
    def downloader(**_kwargs: object) -> pd.DataFrame:
        frame = make_raw_frame("AAPL")["AAPL"].drop(columns=["Adj Close"])
        return pd.concat({"AAPL": frame}, axis=1)

    provider = YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: RETRIEVED_AT,
    )

    result = provider.get_daily_bars(
        (AAPL,),
        date(2026, 1, 1),
        date(2026, 1, 4),
    )

    assert AAPL_ID not in result.frames
    assert result.issues[AAPL_ID].code == YFinanceProviderIssueCode.NORMALIZATION_ERROR
