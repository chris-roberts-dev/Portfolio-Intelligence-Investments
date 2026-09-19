"""Time-bounded strategy context for deterministic Phase 6 backtesting.

Development guide references: Sections 14.4, 14.7, and 19.6.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from portfolio_engine.backtesting.contracts import OrderIntent, PortfolioState
from portfolio_engine.contracts.market_data import PriceFrame


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Immutable strategy view whose price history is capped at ``as_of``."""

    as_of: date
    history: Mapping[UUID, PriceFrame]
    portfolio: PortfolioState
    observation_count: int


class BacktestStrategy(Protocol):
    """Minimal internal strategy boundary used by the deterministic engine."""

    name: str
    version: str
    minimum_history_observations: int

    def generate_orders(self, context: StrategyContext) -> Sequence[OrderIntent]: ...


def build_strategy_context(
    *,
    as_of: date,
    usable_frames: Mapping[UUID, PriceFrame],
    portfolio: PortfolioState,
    observation_count: int,
) -> StrategyContext:
    """Build a structurally time-bounded strategy context."""
    visible: dict[UUID, PriceFrame] = {}
    for asset_id, frame in usable_frames.items():
        capped = tuple(bar for bar in frame if bar.trade_date <= as_of)
        if any(bar.trade_date > as_of for bar in capped):
            raise AssertionError("Strategy history contains a future observation.")
        visible[asset_id] = capped

    return StrategyContext(
        as_of=as_of,
        history=MappingProxyType(visible),
        portfolio=portfolio,
        observation_count=observation_count,
    )
