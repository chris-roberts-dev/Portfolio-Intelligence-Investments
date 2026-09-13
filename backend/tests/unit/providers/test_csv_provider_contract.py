"""Shared provider-contract tests exercised against the CSV provider."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from uuid import UUID

from apps.market_data.providers.base import ProviderIssue
from apps.market_data.providers.csv import (
    CSV_BAR_COLUMNS,
    CsvMarketDataProvider,
)
from portfolio_engine.contracts.market_data import PriceFrame
from tests.unit.providers.provider_contract import (
    ASSET_A_ID,
    ASSET_B_ID,
    MarketDataProviderContract,
)


def write_frame_to_csv(
    path: Path,
    frame: PriceFrame,
) -> None:
    """Serialize canonical fixture values into the explicit CSV provider schema."""
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_BAR_COLUMNS,
        )
        writer.writeheader()

        for bar in frame:
            writer.writerow(
                {
                    "trade_date": bar.trade_date.isoformat(),
                    "open": "" if bar.open is None else bar.open,
                    "high": "" if bar.high is None else bar.high,
                    "low": "" if bar.low is None else bar.low,
                    "close": "" if bar.close is None else bar.close,
                    "adjusted_close": ("" if bar.adjusted_close is None else bar.adjusted_close),
                    "volume": "" if bar.volume is None else bar.volume,
                }
            )


def build_contract(
    tmp_path: Path,
) -> MarketDataProviderContract:
    """Create the reusable contract with a local-path CSV provider factory."""

    def make_csv_provider(
        fixtures: Mapping[UUID, PriceFrame],
        issues: Mapping[UUID, ProviderIssue],
        retrieved_at: datetime,
    ) -> CsvMarketDataProvider:
        paths: dict[str, Path] = {}
        provider_symbols = {
            ASSET_A_ID: "AAA",
            ASSET_B_ID: "BBB",
        }

        for asset_id, frame in fixtures.items():
            provider_symbol = provider_symbols[asset_id]
            path = tmp_path / f"{provider_symbol}.csv"
            write_frame_to_csv(path, frame)
            paths[provider_symbol] = path

        return CsvMarketDataProvider(
            paths,
            issues=issues,
            retrieved_at=retrieved_at,
        )

    return MarketDataProviderContract(
        make_csv_provider,
        provider_name="csv",
    )


def test_csv_provider_preserves_multi_asset_association(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_multi_asset_association()


def test_csv_provider_returns_valid_ordered_unique_bars(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_returned_bars_are_valid()


def test_csv_provider_honors_inclusive_start_exclusive_end(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_inclusive_start_exclusive_end()


def test_csv_provider_preserves_empty_results(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_empty_fixture_remains_empty()


def test_csv_provider_supports_configured_no_data_issue(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_configured_no_data_issue()


def test_csv_provider_preserves_success_during_partial_failure(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_partial_failure_preserves_success()


def test_csv_provider_retains_batch_provenance(
    tmp_path: Path,
) -> None:
    build_contract(tmp_path).assert_batch_provenance()
