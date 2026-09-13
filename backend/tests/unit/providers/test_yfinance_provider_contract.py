"""Shared provider-contract tests exercised against the yfinance adapter."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

import pandas as pd

from apps.market_data.providers.base import ProviderIssue
from apps.market_data.providers.yfinance import YFinanceMarketDataProvider
from portfolio_engine.contracts.market_data import PriceFrame
from tests.unit.providers.provider_contract import (
    ASSET_A_ID,
    ASSET_B_ID,
    MarketDataProviderContract,
)

_PROVIDER_SYMBOLS = {
    ASSET_A_ID: "AAA",
    ASSET_B_ID: "BBB",
}


def _raw_symbol_frame(frame: PriceFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [bar.open for bar in frame],
            "High": [bar.high for bar in frame],
            "Low": [bar.low for bar in frame],
            "Close": [bar.close for bar in frame],
            "Adj Close": [bar.adjusted_close for bar in frame],
            "Volume": [bar.volume for bar in frame],
        },
        index=pd.DatetimeIndex(
            [bar.trade_date for bar in frame],
            name="Date",
        ),
    )


def _combine_symbol_frames(
    frames: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()

    return pd.concat(dict(frames), axis=1)


def make_yfinance_provider(
    fixtures: Mapping[UUID, PriceFrame],
    issues: Mapping[UUID, ProviderIssue],
    retrieved_at: datetime,
) -> YFinanceMarketDataProvider:
    raw_by_symbol = {
        _PROVIDER_SYMBOLS[asset_id]: _raw_symbol_frame(frame)
        for asset_id, frame in fixtures.items()
        if frame and asset_id not in issues
    }

    def downloader(**kwargs: object) -> pd.DataFrame:
        tickers = cast(list[str], kwargs["tickers"])
        selected = {ticker: raw_by_symbol[ticker] for ticker in tickers if ticker in raw_by_symbol}
        return _combine_symbol_frames(selected)

    return YFinanceMarketDataProvider(
        downloader=downloader,
        clock=lambda: retrieved_at,
    )


CONTRACT = MarketDataProviderContract(
    make_yfinance_provider,
    provider_name="yfinance",
)


def test_yfinance_provider_preserves_multi_asset_association() -> None:
    CONTRACT.assert_multi_asset_association()


def test_yfinance_provider_returns_valid_ordered_unique_bars() -> None:
    CONTRACT.assert_returned_bars_are_valid()


def test_yfinance_provider_honors_inclusive_start_exclusive_end() -> None:
    CONTRACT.assert_inclusive_start_exclusive_end()


def test_yfinance_provider_maps_empty_history_to_no_data() -> None:
    CONTRACT.assert_empty_fixture_remains_empty(
        expected_issue_code="NO_DATA",
    )


def test_yfinance_provider_supports_no_data_outcomes() -> None:
    CONTRACT.assert_configured_no_data_issue()


def test_yfinance_provider_preserves_success_during_partial_missing_data() -> None:
    CONTRACT.assert_partial_failure_preserves_success(
        expected_issue_code="NO_DATA",
    )


def test_yfinance_provider_retains_batch_provenance() -> None:
    CONTRACT.assert_batch_provenance()
