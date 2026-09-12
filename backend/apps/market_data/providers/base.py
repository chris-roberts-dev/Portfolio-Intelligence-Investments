"""Provider-neutral market-data boundary.

Development guide reference: Section 9.1.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from portfolio_engine.contracts.market_data import PriceFrame


@dataclass(frozen=True, slots=True)
class ResolvedProviderAsset:
    """Internal asset identity resolved to a provider-specific symbol."""

    asset_id: UUID
    canonical_symbol: str
    provider_symbol: str


@dataclass(frozen=True, slots=True)
class ProviderIssue:
    """Stable provider-boundary diagnostic before API status mapping."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ProviderBatchResult:
    """Provider result keyed by internal asset identity with retrieval provenance."""

    frames: Mapping[UUID, PriceFrame]
    issues: Mapping[UUID, ProviderIssue]
    retrieved_at: datetime


@runtime_checkable
class MarketDataProvider(Protocol):
    """Provider-neutral contract for bounded daily market-bar retrieval."""

    @property
    def name(self) -> str:
        """Return the registered provider name."""
        ...

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        """Return daily bars for resolved assets over [start, end)."""
        ...
