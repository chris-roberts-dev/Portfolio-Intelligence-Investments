"""Provider-neutral application contracts for daily market-bar queries.

Development guide references: Sections 8.4, 9.2, and 27.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from portfolio_engine.config import (
    MAX_BAR_QUERY_CALENDAR_DAYS,
    MAX_BAR_QUERY_ROWS,
    MAX_BAR_QUERY_SYMBOLS,
)
from portfolio_engine.contracts.market_data import PriceFrame


class MarketBarInterval(StrEnum):
    """Market-bar intervals supported by the current application contract."""

    DAILY = "1d"


class MarketBarStatus(StrEnum):
    """Canonical per-symbol market-bar result states."""

    SUCCEEDED = "SUCCEEDED"
    NOT_FOUND = "NOT_FOUND"
    NO_DATA = "NO_DATA"
    FAILED = "FAILED"


class MarketBarQueryErrorCode(StrEnum):
    """Stable validation codes for malformed or unbounded bar queries."""

    EMPTY_SYMBOLS = "EMPTY_SYMBOLS"
    EMPTY_SYMBOL = "EMPTY_SYMBOL"
    TOO_MANY_SYMBOLS = "TOO_MANY_SYMBOLS"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    HISTORY_LIMIT_EXCEEDED = "HISTORY_LIMIT_EXCEEDED"
    ROW_LIMIT_EXCEEDED = "ROW_LIMIT_EXCEEDED"
    UNSUPPORTED_INTERVAL = "UNSUPPORTED_INTERVAL"
    INVALID_PROVIDER = "INVALID_PROVIDER"


class MarketBarQueryError(ValueError):
    """Raised when a market-bar query violates the application contract."""

    def __init__(
        self,
        code: MarketBarQueryErrorCode,
        message: str,
        *,
        field: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


@dataclass(frozen=True, slots=True)
class MarketBarQueryLimits:
    """Bounds applied to a normalized daily-bar request."""

    max_symbols: int = MAX_BAR_QUERY_SYMBOLS
    max_calendar_days: int = MAX_BAR_QUERY_CALENDAR_DAYS
    max_rows: int = MAX_BAR_QUERY_ROWS

    def __post_init__(self) -> None:
        if self.max_symbols < 1:
            raise ValueError("max_symbols must be positive")
        if self.max_calendar_days < 1:
            raise ValueError("max_calendar_days must be positive")
        if self.max_rows < 1:
            raise ValueError("max_rows must be positive")


DEFAULT_MARKET_BAR_QUERY_LIMITS = MarketBarQueryLimits()


@dataclass(frozen=True, slots=True)
class NormalizedMarketBarQuery:
    """Validated and normalized provider-neutral daily-bar request."""

    symbols: tuple[str, ...]
    start: date
    end: date
    interval: MarketBarInterval
    provider: str | None

    @property
    def calendar_days(self) -> int:
        """Return the inclusive-start/exclusive-end calendar span."""
        return (self.end - self.start).days

    @property
    def estimated_max_rows(self) -> int:
        """Return the conservative row upper bound used for request validation."""
        return len(self.symbols) * self.calendar_days


@dataclass(frozen=True, slots=True)
class MarketBarSymbolResult:
    """Canonical result for one normalized request symbol."""

    symbol: str
    asset_id: UUID | None
    status: MarketBarStatus
    bars: PriceFrame = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must not be empty")

        if self.status is MarketBarStatus.SUCCEEDED:
            if self.asset_id is None:
                raise ValueError("SUCCEEDED results require asset_id")
            if not self.bars:
                raise ValueError("SUCCEEDED results require at least one bar")
            return

        if self.bars:
            raise ValueError("Only SUCCEEDED results may contain bars")

        if self.status is MarketBarStatus.NO_DATA and self.asset_id is None:
            raise ValueError("NO_DATA results require asset_id")


@dataclass(frozen=True, slots=True)
class MarketBarBatchMeta:
    """Batch-level provider and request provenance."""

    provider: str
    retrieved_at: datetime
    interval: MarketBarInterval
    start: date
    end: date

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be blank")
        if self.start >= self.end:
            raise ValueError("start must be earlier than end")


@dataclass(frozen=True, slots=True)
class MarketBarBatchResult:
    """Ordered symbol results with shared batch provenance."""

    results: tuple[MarketBarSymbolResult, ...]
    meta: MarketBarBatchMeta

    @property
    def row_count(self) -> int:
        """Return the total number of canonical bars in the batch."""
        return sum(len(result.bars) for result in self.results)


def normalize_market_bar_query(
    symbols: Sequence[str],
    *,
    start: date,
    end: date,
    interval: str | MarketBarInterval = MarketBarInterval.DAILY,
    provider: str | None = None,
    limits: MarketBarQueryLimits = DEFAULT_MARKET_BAR_QUERY_LIMITS,
) -> NormalizedMarketBarQuery:
    """Validate and normalize a bounded daily market-bar query.

    ``start`` is inclusive and ``end`` is exclusive. Symbols are trimmed,
    uppercased for the U.S.-listed MVP universe, and de-duplicated while
    preserving their first canonical occurrence.

    This function performs no provider lookup, provider allowlist check,
    network I/O, persistence, or authorization.
    """
    raw_symbols = tuple(symbols)

    if not raw_symbols:
        raise MarketBarQueryError(
            MarketBarQueryErrorCode.EMPTY_SYMBOLS,
            "At least one symbol is required.",
            field="symbols",
        )

    if len(raw_symbols) > limits.max_symbols:
        raise MarketBarQueryError(
            MarketBarQueryErrorCode.TOO_MANY_SYMBOLS,
            f"No more than {limits.max_symbols} symbols may be supplied.",
            field="symbols",
        )

    normalized_symbols: list[str] = []
    seen_symbols: set[str] = set()

    for raw_symbol in raw_symbols:
        symbol = raw_symbol.strip().upper()

        if not symbol:
            raise MarketBarQueryError(
                MarketBarQueryErrorCode.EMPTY_SYMBOL,
                "Symbols must not be blank.",
                field="symbols",
            )

        if symbol not in seen_symbols:
            seen_symbols.add(symbol)
            normalized_symbols.append(symbol)

    if isinstance(interval, MarketBarInterval):
        normalized_interval = interval
    else:
        try:
            normalized_interval = MarketBarInterval(interval)
        except ValueError as exc:
            raise MarketBarQueryError(
                MarketBarQueryErrorCode.UNSUPPORTED_INTERVAL,
                "Only the 1d interval is supported.",
                field="interval",
            ) from exc

    if start >= end:
        raise MarketBarQueryError(
            MarketBarQueryErrorCode.INVALID_DATE_RANGE,
            "start must be earlier than end.",
            field="end",
        )

    calendar_days = (end - start).days

    if calendar_days > limits.max_calendar_days:
        raise MarketBarQueryError(
            MarketBarQueryErrorCode.HISTORY_LIMIT_EXCEEDED,
            (f"Requested history exceeds the configured {limits.max_calendar_days}-day limit."),
            field="end",
        )

    estimated_max_rows = len(normalized_symbols) * calendar_days

    if estimated_max_rows > limits.max_rows:
        raise MarketBarQueryError(
            MarketBarQueryErrorCode.ROW_LIMIT_EXCEEDED,
            (f"Requested symbols and date span exceed the configured {limits.max_rows}-row limit."),
            field="symbols",
        )

    normalized_provider: str | None = None

    if provider is not None:
        normalized_provider = provider.strip().lower()

        if not normalized_provider:
            raise MarketBarQueryError(
                MarketBarQueryErrorCode.INVALID_PROVIDER,
                "provider must not be blank when supplied.",
                field="provider",
            )

    return NormalizedMarketBarQuery(
        symbols=tuple(normalized_symbols),
        start=start,
        end=end,
        interval=normalized_interval,
        provider=normalized_provider,
    )
