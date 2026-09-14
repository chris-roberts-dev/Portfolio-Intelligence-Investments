"""yfinance market-data provider adapter.

All yfinance loading is intentionally confined to this module.

Development guide references: Sections 4.4, 9.1, 9.5, 9.6, and 9.7.
"""

from __future__ import annotations

import importlib
import math
import random
import time
from collections import deque
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
from apps.market_data.providers.safety import safe_provider_issue
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_validation import (
    MarketDataQualityError,
    validate_price_frame,
)
from portfolio_engine.contracts.provider_execution import (
    ProviderExecutionFailure,
    ProviderExecutionPolicy,
    ProviderFailureCode,
    ProviderRateLimitPolicy,
)

type YFinanceDownloader = Callable[..., pd.DataFrame | None]
type Clock = Callable[[], datetime]
type Sleeper = Callable[[float], None]
type JitterSampler = Callable[[float, float], float]
type MonotonicClock = Callable[[], float]

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

YFINANCE_RATE_LIMIT_POLICY = ProviderRateLimitPolicy(
    max_requests=1,
    window_seconds=1.0,
)

YFINANCE_EXECUTION_POLICY = ProviderExecutionPolicy(
    rate_limit=YFINANCE_RATE_LIMIT_POLICY,
)


class YFinanceProviderIssueCode(StrEnum):
    """Stable per-asset issue codes emitted by the yfinance adapter."""

    NO_DATA = "NO_DATA"
    THROTTLED = "THROTTLED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    NORMALIZATION_ERROR = "NORMALIZATION_ERROR"
    DATA_QUALITY_ERROR = "DATA_QUALITY_ERROR"


class _DownloadAttemptsExhausted(RuntimeError):
    """Internal signal that a provider download cannot be attempted again."""

    def __init__(
        self,
        failure: ProviderExecutionFailure,
        *,
        attempts_made: int,
    ) -> None:
        super().__init__(failure.message)
        self.failure = failure
        self.attempts_made = attempts_made


class YFinanceMarketDataProvider:
    """Normalize yfinance daily downloads into canonical price frames."""

    name = "yfinance"

    def __init__(
        self,
        *,
        downloader: YFinanceDownloader | None = None,
        clock: Clock | None = None,
        execution_policy: ProviderExecutionPolicy = YFINANCE_EXECUTION_POLICY,
        sleeper: Sleeper | None = None,
        jitter_sampler: JitterSampler | None = None,
        monotonic_clock: MonotonicClock | None = None,
    ) -> None:
        self._downloader = downloader or _download_yfinance
        self._clock = clock or _utc_now
        self._execution_policy = execution_policy
        self._sleeper = sleeper or time.sleep
        self._jitter_sampler = jitter_sampler or random.uniform
        self._monotonic_clock = monotonic_clock or time.monotonic
        self._request_times: deque[float] = deque()

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
            downloaded = self._download_with_execution_policy(
                provider_symbols,
                start=start,
                end=end,
            )
        except _DownloadAttemptsExhausted as exc:
            issue_code = (
                YFinanceProviderIssueCode.THROTTLED
                if exc.failure.code is ProviderFailureCode.THROTTLED
                else YFinanceProviderIssueCode.PROVIDER_ERROR
            )
            return _batch_failure(
                assets,
                retrieved_at=retrieved_at,
                code=issue_code,
                message=(
                    "yfinance download failed after "
                    f"{exc.attempts_made} attempt(s): {exc.failure.message}"
                ),
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
                issues[asset.asset_id] = safe_provider_issue(
                    YFinanceProviderIssueCode.NO_DATA,
                    (
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
                    issues[asset.asset_id] = safe_provider_issue(
                        YFinanceProviderIssueCode.NO_DATA,
                        (
                            "yfinance returned no usable history for provider symbol "
                            f"{asset.provider_symbol!r}."
                        ),
                    )
                    continue

                validate_price_frame(frame)
            except MarketDataQualityError as exc:
                issues[asset.asset_id] = safe_provider_issue(
                    YFinanceProviderIssueCode.DATA_QUALITY_ERROR,
                    str(exc),
                )
                continue
            except (KeyError, TypeError, ValueError) as exc:
                issues[asset.asset_id] = safe_provider_issue(
                    YFinanceProviderIssueCode.NORMALIZATION_ERROR,
                    str(exc),
                )
                continue

            frames[asset.asset_id] = frame

        return ProviderBatchResult(
            frames=MappingProxyType(frames),
            issues=MappingProxyType(issues),
            retrieved_at=retrieved_at,
        )

    def _download_with_execution_policy(
        self,
        provider_symbols: tuple[str, ...],
        *,
        start: date,
        end: date,
    ) -> pd.DataFrame | None:
        attempts_made = 0

        while True:
            self._acquire_rate_limit_slot()
            attempts_made += 1

            try:
                return self._downloader(
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
                    timeout=self._execution_policy.timeout_seconds,
                )
            except Exception as exc:
                failure = _classify_download_exception(exc)

                if not self._execution_policy.retry.should_retry(
                    failure,
                    attempts_made=attempts_made,
                ):
                    raise _DownloadAttemptsExhausted(
                        failure,
                        attempts_made=attempts_made,
                    ) from exc

                lower_bound, upper_bound = self._execution_policy.retry.backoff_bounds(
                    attempts_made=attempts_made,
                    retry_after_seconds=failure.retry_after_seconds,
                )
                delay = self._jitter_sampler(
                    lower_bound,
                    upper_bound,
                )

                if not lower_bound <= delay <= upper_bound:
                    raise ValueError(
                        "jitter sampler returned a delay outside policy bounds"
                    ) from None

                self._sleeper(delay)

    def _acquire_rate_limit_slot(self) -> None:
        rate_limit = self._execution_policy.rate_limit

        if rate_limit is None:
            return

        now = self._monotonic_clock()
        self._discard_expired_request_times(
            now=now,
            window_seconds=rate_limit.window_seconds,
        )

        if len(self._request_times) >= rate_limit.max_requests:
            ready_at = self._request_times[0] + rate_limit.window_seconds
            delay = max(0.0, ready_at - now)

            if delay > 0.0:
                self._sleeper(delay)

            now = max(
                self._monotonic_clock(),
                ready_at,
            )
            self._discard_expired_request_times(
                now=now,
                window_seconds=rate_limit.window_seconds,
            )

        self._request_times.append(now)

    def _discard_expired_request_times(
        self,
        *,
        now: float,
        window_seconds: float,
    ) -> None:
        cutoff = now - window_seconds

        while self._request_times and self._request_times[0] <= cutoff:
            self._request_times.popleft()


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


def _classify_download_exception(
    exc: Exception,
) -> ProviderExecutionFailure:
    class_name = type(exc).__name__.lower()
    message = str(exc).strip() or type(exc).__name__
    retry_after_seconds = _retry_after_seconds(exc)

    if "ratelimit" in class_name or "throttle" in class_name:
        code = ProviderFailureCode.THROTTLED
    elif isinstance(exc, TimeoutError) or "timeout" in class_name:
        code = ProviderFailureCode.TIMEOUT
    elif (
        isinstance(exc, (ConnectionError, OSError))
        or "connection" in class_name
        or "network" in class_name
    ):
        code = ProviderFailureCode.TRANSIENT
    else:
        code = ProviderFailureCode.NON_RETRYABLE

    return ProviderExecutionFailure(
        code=code,
        message=message,
        retry_after_seconds=retry_after_seconds,
    )


def _retry_after_seconds(
    exc: Exception,
) -> float | None:
    value = getattr(exc, "retry_after_seconds", None)

    if isinstance(value, bool) or not isinstance(value, Real):
        return None

    retry_after = float(value)

    if not math.isfinite(retry_after) or retry_after < 0.0:
        return None

    return retry_after


def _batch_failure(
    assets: Sequence[ResolvedProviderAsset],
    *,
    retrieved_at: datetime,
    code: YFinanceProviderIssueCode,
    message: str,
) -> ProviderBatchResult:
    issues = {
        asset.asset_id: safe_provider_issue(
            code,
            message,
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
