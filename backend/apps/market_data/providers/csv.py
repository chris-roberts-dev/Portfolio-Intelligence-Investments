"""Deterministic offline CSV market-data provider.

Development guide references: Sections 9.1, 9.6, 9.7, and 19.11.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from uuid import UUID

from apps.market_data.providers.base import (
    ProviderBatchResult,
    ProviderIssue,
    ResolvedProviderAsset,
)
from apps.market_data.providers.safety import safe_provider_issue
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_validation import (
    MarketDataQualityError,
    validate_price_frame,
)

CSV_BAR_COLUMNS = (
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
)


class CsvProviderIssueCode(StrEnum):
    """Stable issue codes emitted by the deterministic CSV provider."""

    NO_DATA = "NO_DATA"
    CSV_ERROR = "CSV_ERROR"
    DATA_QUALITY_ERROR = "DATA_QUALITY_ERROR"


class CsvMarketDataProvider:
    """Offline provider backed only by explicitly injected local CSV paths."""

    name = "csv"

    def __init__(
        self,
        paths: Mapping[str, str | Path],
        *,
        retrieved_at: datetime,
        issues: Mapping[UUID, ProviderIssue] | None = None,
    ) -> None:
        normalized_paths: dict[str, Path] = {}

        for provider_symbol, path in paths.items():
            if not provider_symbol.strip():
                raise ValueError("CSV provider symbols must not be blank.")

            normalized_paths[provider_symbol] = Path(path)

        self._paths: Mapping[str, Path] = MappingProxyType(normalized_paths)
        self._issues: Mapping[UUID, ProviderIssue] = MappingProxyType(
            {
                asset_id: safe_provider_issue(
                    issue.code,
                    issue.message,
                )
                for asset_id, issue in (issues or {}).items()
            }
        )
        self._retrieved_at = retrieved_at

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        """Return validated local CSV bars over inclusive-start/exclusive-end dates."""
        if start >= end:
            raise ValueError("start must be earlier than end")

        frames: dict[UUID, PriceFrame] = {}
        issues: dict[UUID, ProviderIssue] = {}

        for asset in assets:
            configured_issue = self._issues.get(asset.asset_id)

            if configured_issue is not None:
                issues[asset.asset_id] = configured_issue
                continue

            path = self._paths.get(asset.provider_symbol)

            if path is None:
                issues[asset.asset_id] = safe_provider_issue(
                    CsvProviderIssueCode.NO_DATA,
                    (f"No CSV path is configured for provider symbol {asset.provider_symbol!r}."),
                )
                continue

            try:
                source_frame = self._read_frame(path, asset)
                validate_price_frame(source_frame)

                filtered_frame: PriceFrame = tuple(
                    bar for bar in source_frame if start <= bar.trade_date < end
                )

                validate_price_frame(filtered_frame)
            except MarketDataQualityError as exc:
                issues[asset.asset_id] = safe_provider_issue(
                    CsvProviderIssueCode.DATA_QUALITY_ERROR,
                    str(exc),
                )
                continue
            except (csv.Error, OSError, ValueError) as exc:
                issues[asset.asset_id] = safe_provider_issue(
                    CsvProviderIssueCode.CSV_ERROR,
                    str(exc),
                )
                continue

            frames[asset.asset_id] = filtered_frame

        return ProviderBatchResult(
            frames=MappingProxyType(frames),
            issues=MappingProxyType(issues),
            retrieved_at=self._retrieved_at,
        )

    def _read_frame(
        self,
        path: Path,
        asset: ResolvedProviderAsset,
    ) -> PriceFrame:
        with path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            if tuple(reader.fieldnames or ()) != CSV_BAR_COLUMNS:
                raise ValueError("CSV header must exactly match: " + ",".join(CSV_BAR_COLUMNS))

            return tuple(self._parse_bar(row, asset) for row in reader)

    def _parse_bar(
        self,
        row: Mapping[str, str | None],
        asset: ResolvedProviderAsset,
    ) -> PriceBar:
        return PriceBar(
            asset_id=asset.asset_id,
            trade_date=date.fromisoformat(self._required_value(row, "trade_date")),
            open=self._optional_float(row, "open"),
            high=self._optional_float(row, "high"),
            low=self._optional_float(row, "low"),
            close=self._optional_float(row, "close"),
            adjusted_close=self._optional_float(row, "adjusted_close"),
            volume=self._optional_int(row, "volume"),
            source=self.name,
            retrieved_at=self._retrieved_at,
        )

    @staticmethod
    def _required_value(
        row: Mapping[str, str | None],
        field: str,
    ) -> str:
        value = row.get(field)

        if value is None or not value.strip():
            raise ValueError(f"CSV field {field!r} must not be blank.")

        return value.strip()

    @staticmethod
    def _optional_float(
        row: Mapping[str, str | None],
        field: str,
    ) -> float | None:
        value = row.get(field)

        if value is None or not value.strip():
            return None

        return float(value)

    @staticmethod
    def _optional_int(
        row: Mapping[str, str | None],
        field: str,
    ) -> int | None:
        value = row.get(field)

        if value is None or not value.strip():
            return None

        return int(value)
