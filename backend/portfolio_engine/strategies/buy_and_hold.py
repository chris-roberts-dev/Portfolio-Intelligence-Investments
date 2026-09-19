"""Canonical long-only buy-and-hold strategy for Phase 6.

Development guide references: Sections 9.6-9.7, 14.3-14.7, 17.1,
19.6, and 23.7.

Initial allocation semantics are deliberately explicit: the strategy begins
from cash, observes the first eligible aligned adjusted-close observation,
creates buy intents targeting the configured fully-invested risky-asset
weights using that decision-date portfolio value, and relies on the execution
layer to fill on the next aligned observation. Commission, slippage, and any
required proportional buy scaling are owned by the execution layer. After a
security position exists, the strategy emits no further orders.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import NoReturn
from uuid import UUID

from portfolio_engine.backtesting import (
    BacktestError,
    BacktestErrorCode,
    OrderIntent,
    OrderSide,
    StrategyContext,
)
from portfolio_engine.config import WEIGHT_SUM_TOLERANCE

BUY_AND_HOLD_STRATEGY_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class BuyAndHoldTargetWeight:
    """One canonical risky-asset target weight for initial allocation."""

    asset_id: UUID
    weight: float


@dataclass(frozen=True, slots=True)
class BuyAndHoldStrategy:
    """Buy once on the first eligible decision and hold thereafter."""

    targets: tuple[BuyAndHoldTargetWeight, ...]
    name: str = field(init=False, default="BUY_AND_HOLD")
    version: str = field(init=False, default=BUY_AND_HOLD_STRATEGY_VERSION)
    minimum_history_observations: int = field(init=False, default=1)

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", _normalize_targets(self.targets))

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        """Create the one initial allocation decision from information through ``as_of``."""
        if context.portfolio.positions:
            return ()
        if context.portfolio.cash <= WEIGHT_SUM_TOLERANCE:
            return ()

        orders: list[OrderIntent] = []
        for target in self.targets:
            if target.weight <= WEIGHT_SUM_TOLERANCE:
                continue
            frame = context.history.get(target.asset_id)
            if not frame:
                _raise(
                    BacktestErrorCode.INVALID_PRICE_HISTORY,
                    f"Buy-and-hold target asset {target.asset_id} has no visible history.",
                )
            latest = frame[-1]
            if latest.trade_date != context.as_of or latest.adjusted_close is None:
                _raise(
                    BacktestErrorCode.INVALID_PRICE_HISTORY,
                    (
                        "Buy-and-hold requires an adjusted-close observation on the "
                        f"decision date for asset {target.asset_id}."
                    ),
                )
            price = float(latest.adjusted_close)
            if not math.isfinite(price) or price <= 0.0:
                _raise(
                    BacktestErrorCode.INVALID_PRICE_HISTORY,
                    f"Buy-and-hold decision price for asset {target.asset_id} must be positive.",
                )
            quantity = context.portfolio.total_value * target.weight / price
            if quantity <= WEIGHT_SUM_TOLERANCE:
                continue
            orders.append(
                OrderIntent(
                    asset_id=target.asset_id,
                    side=OrderSide.BUY,
                    quantity=quantity,
                )
            )
        return tuple(orders)


def _normalize_targets(
    targets: tuple[BuyAndHoldTargetWeight, ...],
) -> tuple[BuyAndHoldTargetWeight, ...]:
    if not targets:
        _raise(BacktestErrorCode.INVALID_INPUT, "Buy-and-hold requires target weights.")

    seen: set[UUID] = set()
    normalized: list[BuyAndHoldTargetWeight] = []
    for index, target in enumerate(targets):
        if target.asset_id in seen:
            _raise(
                BacktestErrorCode.INVALID_INPUT,
                f"Duplicate buy-and-hold target asset at index {index}.",
            )
        seen.add(target.asset_id)
        if isinstance(target.weight, bool) or not isinstance(target.weight, (int, float)):
            _raise(
                BacktestErrorCode.INVALID_INPUT,
                f"targets[{index}].weight must be a real number.",
            )
        weight = float(target.weight)
        if not math.isfinite(weight) or weight < 0.0 or weight > 1.0:
            _raise(
                BacktestErrorCode.INVALID_INPUT,
                f"targets[{index}].weight must be finite and between zero and one.",
            )
        normalized.append(BuyAndHoldTargetWeight(asset_id=target.asset_id, weight=weight))

    total = math.fsum(target.weight for target in normalized)
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        _raise(
            BacktestErrorCode.INVALID_INPUT,
            "Buy-and-hold target weights must sum to one within tolerance.",
        )
    if not any(target.weight > WEIGHT_SUM_TOLERANCE for target in normalized):
        _raise(BacktestErrorCode.INVALID_INPUT, "Buy-and-hold requires a positive target weight.")

    return tuple(sorted(normalized, key=lambda item: str(item.asset_id)))


def _raise(code: BacktestErrorCode, message: str) -> NoReturn:
    raise BacktestError(code, message)
