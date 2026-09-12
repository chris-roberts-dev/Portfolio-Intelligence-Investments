"""Canonical framework-independent market-data contracts.

Development guide references: Sections 8.3 and 9.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PriceBar:
    """Canonical normalized daily price-bar record.

    Values are deliberately not validated in this contract module. Phase 2
    normalization and data-quality services enforce positivity, OHLC
    relationships, ordering, uniqueness, missingness, and requested-period
    coverage before frames enter analytical code.
    """

    asset_id: UUID
    trade_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adjusted_close: float | None
    volume: int | None
    source: str
    retrieved_at: datetime


type PriceFrame = tuple[PriceBar, ...]
