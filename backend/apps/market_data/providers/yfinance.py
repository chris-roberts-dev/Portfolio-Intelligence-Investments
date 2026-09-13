"""yfinance market-data provider adapter.

All yfinance loading is intentionally confined to this module.

Development guide references: Sections 4.4, 9.1, 9.5, 9.6, and 9.7.
"""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from enum import StrEnum
from numbers import Real
from types import MappingProxyType
from typing import cast
from uuid import UUID

import pandas as pd

from apps.market_data.providers.base import (
    ProviderBatchResult,
    ProviderIssue,
    ResolvedProviderAsset,
)
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_validation import (
    MarketDataQualityError,
    validate_price_frame,
)

type YFinanceDownloader = Callable[..., pd.DataFrame | None]
type Clock = Callable[[], datetime]

_REQUIRED_PRICE_COLUMNS = frozenset(
    {
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
    }
)


class YFinanceProviderIssueCode(StrEnum):
    """Stable per-asset issue codes emitted by the yfinance adapter."""

    NO_DATA = "NO_DATA"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    DATA_QUALITY_ERROR = "DATA_QUALITY_ERROR"


class YFinanceMarketDataProvider:
    """Normalize yfinance daily downloads into canonical price frames."""

    name = "yfinance"

    def __init__(
        self,
        *,
        downloader: YFinanceDownloader | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._downloader = downloader or _download_yfinance
        self._clock = clock or _utc_now

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        """Retrieve and normalize daily bars for pre-resolved provider assets."""
        if start >= end:
            raise ValueError("start must be earlier than end")

        retrieved_at = self._clock()

        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError("yfinance provider clock must return a timezone-aware datetime")

        if not assets:
            return ProviderBatchResult(
                frames=MappingProxyType({}),
                issues=MappingProxyType({}),
                retrieved_at=retrieved_at,
            )

        provider_symbols = tuple(dict.fromkeys(asset.provider_symbol for asset in assets))

        try:
            downloaded = self._downloader(
                tickers=list(provider_symbols),
                start=start.isoformat(),
                end=end.isoformat(),
                interval="1d",
                actions=False,
                auto_adjust=False,
                repair=False,
                keepna=True,
                group_by="ticker",
                ignore_tz=True,
                rounding=False,
                progress=False,
                threads=False,
                multi_level_index=True,
            )
        except Exception as exc:
            return _batch_failure(
                assets,
                retrieved_at=retrieved_at,
                code=YFinanceProviderIssueCode.PROVIDER_ERROR,
                message=f"yfinance download failed: {exc}",
            )

        if downloaded is None or downloaded.empty:
            return _batch_failure(
                assets,
                retrieved_at=retrieved_at,
                code=YFinanceProviderIssueCode.NO_DATA,
                message="yfinance returned no history for the requested period.",
            )

        frames: dict[UUID, PriceFrame] = {}
        issues: dict[UUID, ProviderIssue] = {}

        for asset in assets:
            try:
                symbol_frame = _extract_symbol_frame(
                    downloaded,
                    asset.provider_symbol,
                    requested_symbol_count=len(provider_symbols),
                )
            except KeyError:
                issues[asset.asset_id] = ProviderIssue(
                    code=YFinanceProviderIssueCode.NO_DATA,
                    message=(
                        "yfinance returned no history for provider symbol "
                        f"{asset.provider_symbol!r}."
                    ),
                )
                continue

            try:
                frame = _normalize_symbol_frame(
                    symbol_frame,
                    asset=asset,
                    start=start,
                    end=end,
                    retrieved_at=retrieved_at,
                )

                if not frame or _contains_no_observed_market_values(frame):
                    issues[asset.asset_id] = ProviderIssue(
                        code=YFinanceProviderIssueCode.NO_DATA,
                        message=(
                            "yfinance returned no usable history for provider symbol "
                            f"{asset.provider_symbol!r}."
                        ),
                    )
                    continue

                validate_price_frame(frame)
            except MarketDataQualityError as exc:
                issues[asset.asset_id] = ProviderIssue(
                    code=YFinanceProviderIssueCode.DATA_QUALITY_ERROR,
                    message=str(exc),
                )
                continue
            except (KeyError, TypeError, ValueError) as exc:
                issues[asset.asset_id] = ProviderIssue(
                    code=YFinanceProviderIssueCode.NORMALIZATION_ERROR,
                    message=str(exc),
                )
                continue

            frames[asset.asset_id] = frame

        return ProviderBatchResult(
            frames=MappingProxyType(frames),
            issues=MappingProxyType(issues),
            retrieved_at=retrieved_at,
        )


def _download_yfinance(**kwargs: object) -> pd.DataFrame | None:
    """Load yfinance lazily so provider-specific loading stays in this module."""
    yfinance_module = importlib.import_module("yfinance")
    download = cast(
        Callable[..., object],
        yfinance_module.download,
    )
    result = download(**kwargs)

    if result is None:
        return None

    if not isinstance(result, pd.DataFrame):
        raise TypeError("yfinance.download() must return a pandas DataFrame or None")

    return result


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _batch_failure(
    assets: Sequence[ResolvedProviderAsset],
    *,
    retrieved_at: datetime,
    code: YFinanceProviderIssueCode,
    message: str,
) -> ProviderBatchResult:
    issues = {
        asset.asset_id: ProviderIssue(
            code=code,
            message=message,
        )
        for asset in assets
    }

    return ProviderBatchResult(
        frames=MappingProxyType({}),
        issues=MappingProxyType(issues),
        retrieved_at=retrieved_at,
    )


def _extract_symbol_frame(
    downloaded: pd.DataFrame,
    provider_symbol: str,
    *,
    requested_symbol_count: int,
) -> pd.DataFrame:
    if isinstance(downloaded.columns, pd.MultiIndex):
        for level in range(downloaded.columns.nlevels):
            labels = {str(value) for value in downloaded.columns.get_level_values(level)}

            if provider_symbol not in labels:
                continue

            extracted = downloaded.xs(
                provider_symbol,
                axis=1,
                level=level,
                drop_level=True,
            )

            if isinstance(extracted, pd.Series):
                return extracted.to_frame()

            return extracted.copy()

        raise KeyError(f"No yfinance columns were returned for {provider_symbol!r}")

    if requested_symbol_count == 1:
        return downloaded.copy()

    raise KeyError(f"No yfinance columns were returned for {provider_symbol!r}")


def _normalize_symbol_frame(
    symbol_frame: pd.DataFrame,
    *,
    asset: ResolvedProviderAsset,
    start: date,
    end: date,
    retrieved_at: datetime,
) -> PriceFrame:
    column_names = {str(column) for column in symbol_frame.columns}
    missing_columns = sorted(_REQUIRED_PRICE_COLUMNS - column_names)

    if missing_columns:
        raise ValueError(
            "yfinance output is missing required columns: " + ", ".join(missing_columns)
        )

    bars: list[PriceBar] = []

    for index_value, row in symbol_frame.iterrows():
        trade_date = _trade_date_from_index(index_value)

        if not start <= trade_date < end:
            continue

        bars.append(
            PriceBar(
                asset_id=asset.asset_id,
                trade_date=trade_date,
                open=_optional_float(row["Open"], field="Open"),
                high=_optional_float(row["High"], field="High"),
                low=_optional_float(row["Low"], field="Low"),
                close=_optional_float(row["Close"], field="Close"),
                adjusted_close=_optional_float(
                    row["Adj Close"],
                    field="Adj Close",
                ),
                volume=_optional_int(row["Volume"], field="Volume"),
                source=YFinanceMarketDataProvider.name,
                retrieved_at=retrieved_at,
            )
        )

    return tuple(bars)


def _trade_date_from_index(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"yfinance date index value {value!r} is not a valid ISO date"
            ) from exc

    raise ValueError("yfinance daily output must use date-like index values")


def _optional_float(
    value: object,
    *,
    field: str,
) -> float | None:
    if value is None or value is pd.NA:
        return None

    number = _real_number(value, field=field)

    if math.isnan(number):
        return None

    if not math.isfinite(number):
        raise ValueError(f"yfinance field {field!r} must be finite when present")

    return number


def _optional_int(
    value: object,
    *,
    field: str,
) -> int | None:
    if value is None or value is pd.NA:
        return None

    number = _real_number(value, field=field)

    if math.isnan(number):
        return None

    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"yfinance field {field!r} must be an integer when present")

    return int(number)


def _real_number(
    value: object,
    *,
    field: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"yfinance field {field!r} must be numeric when present")

    return float(value)


def _contains_no_observed_market_values(frame: PriceFrame) -> bool:
    return all(
        bar.open is None
        and bar.high is None
        and bar.low is None
        and bar.close is None
        and bar.adjusted_close is None
        and bar.volume is None
        for bar in frame
    )
