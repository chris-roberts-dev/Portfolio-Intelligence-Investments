"""Deterministic validation for canonical market-data frames.

Development guide references: Sections 8.3, 9.7, and 9.8.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from portfolio_engine.contracts.market_data import PriceFrame


class MarketDataQualityCode(StrEnum):
    """Stable codes for canonical market-data quality failures."""

    DUPLICATE_TRADE_DATE = "DUPLICATE_TRADE_DATE"
    UNSORTED_TRADE_DATES = "UNSORTED_TRADE_DATES"
    NON_POSITIVE_PRICE = "NON_POSITIVE_PRICE"
    HIGH_BELOW_LOW = "HIGH_BELOW_LOW"
    OPEN_OUTSIDE_RANGE = "OPEN_OUTSIDE_RANGE"
    CLOSE_OUTSIDE_RANGE = "CLOSE_OUTSIDE_RANGE"
    NEGATIVE_VOLUME = "NEGATIVE_VOLUME"
    INCONSISTENT_ASSET_ID = "INCONSISTENT_ASSET_ID"
    INCONSISTENT_SOURCE = "INCONSISTENT_SOURCE"
    INCONSISTENT_RETRIEVED_AT = "INCONSISTENT_RETRIEVED_AT"


class MarketDataQualityError(ValueError):
    """Raised when normalized market data violates a canonical quality invariant."""

    def __init__(
        self,
        code: MarketDataQualityCode,
        message: str,
        *,
        trade_date: date | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.trade_date = trade_date
        self.field = field


def validate_price_frame(frame: PriceFrame) -> PriceFrame:
    """Validate a canonical daily price frame without mutating or normalizing it.

    Missing values remain missing. The function does not sort observations,
    remove duplicates, fill gaps, or coerce numeric values.

    Args:
        frame: Immutable sequence of canonical daily price bars.

    Returns:
        The original frame when every canonical data-quality invariant holds.

    Raises:
        MarketDataQualityError: If any frame-level or bar-level invariant fails.
    """
    if not frame:
        return frame

    expected_asset_id = frame[0].asset_id
    expected_source = frame[0].source
    expected_retrieved_at = frame[0].retrieved_at

    seen_dates: set[date] = set()
    previous_trade_date: date | None = None

    for bar in frame:
        if bar.trade_date in seen_dates:
            raise MarketDataQualityError(
                MarketDataQualityCode.DUPLICATE_TRADE_DATE,
                f"Duplicate trade date: {bar.trade_date.isoformat()}",
                trade_date=bar.trade_date,
            )

        if previous_trade_date is not None and bar.trade_date < previous_trade_date:
            raise MarketDataQualityError(
                MarketDataQualityCode.UNSORTED_TRADE_DATES,
                (
                    f"Trade date {bar.trade_date.isoformat()} occurs after "
                    f"{previous_trade_date.isoformat()} in frame order."
                ),
                trade_date=bar.trade_date,
            )

        seen_dates.add(bar.trade_date)
        previous_trade_date = bar.trade_date

        if bar.asset_id != expected_asset_id:
            raise MarketDataQualityError(
                MarketDataQualityCode.INCONSISTENT_ASSET_ID,
                "All bars in a price frame must have the same asset_id.",
                trade_date=bar.trade_date,
                field="asset_id",
            )

        if bar.source != expected_source:
            raise MarketDataQualityError(
                MarketDataQualityCode.INCONSISTENT_SOURCE,
                "All bars in a price frame must have the same source.",
                trade_date=bar.trade_date,
                field="source",
            )

        if bar.retrieved_at != expected_retrieved_at:
            raise MarketDataQualityError(
                MarketDataQualityCode.INCONSISTENT_RETRIEVED_AT,
                "All bars in a price frame must have the same retrieved_at value.",
                trade_date=bar.trade_date,
                field="retrieved_at",
            )

        prices = (
            ("open", bar.open),
            ("high", bar.high),
            ("low", bar.low),
            ("close", bar.close),
            ("adjusted_close", bar.adjusted_close),
        )

        for field_name, value in prices:
            if value is not None and value <= 0:
                raise MarketDataQualityError(
                    MarketDataQualityCode.NON_POSITIVE_PRICE,
                    f"{field_name} must be positive when present.",
                    trade_date=bar.trade_date,
                    field=field_name,
                )

        if bar.high is not None and bar.low is not None:
            if bar.high < bar.low:
                raise MarketDataQualityError(
                    MarketDataQualityCode.HIGH_BELOW_LOW,
                    "high must be greater than or equal to low.",
                    trade_date=bar.trade_date,
                )

            if bar.open is not None and not bar.low <= bar.open <= bar.high:
                raise MarketDataQualityError(
                    MarketDataQualityCode.OPEN_OUTSIDE_RANGE,
                    "open must fall within [low, high] when all values are present.",
                    trade_date=bar.trade_date,
                    field="open",
                )

            if bar.close is not None and not bar.low <= bar.close <= bar.high:
                raise MarketDataQualityError(
                    MarketDataQualityCode.CLOSE_OUTSIDE_RANGE,
                    "close must fall within [low, high] when all values are present.",
                    trade_date=bar.trade_date,
                    field="close",
                )

        if bar.volume is not None and bar.volume < 0:
            raise MarketDataQualityError(
                MarketDataQualityCode.NEGATIVE_VOLUME,
                "volume must be non-negative when present.",
                trade_date=bar.trade_date,
                field="volume",
            )

    return frame
