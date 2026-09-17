"""Framework-independent contracts for Phase 5 rebalancing calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class RebalancingErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_TARGET_WEIGHTS = "INVALID_TARGET_WEIGHTS"
    INVALID_CURRENT_VALUES = "INVALID_CURRENT_VALUES"


class RebalancingError(ValueError):
    """Stable quantitative-engine rebalancing failure."""

    def __init__(self, code: RebalancingErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class RebalanceSchedule(StrEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class SimulatedTradeDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class TargetWeight:
    """One security or cash target. ``asset_id=None`` represents cash."""

    asset_id: UUID | None
    weight: float


@dataclass(frozen=True, slots=True)
class CurrentValue:
    """One current security or cash value. ``asset_id=None`` represents cash."""

    asset_id: UUID | None
    market_value: float


@dataclass(frozen=True, slots=True)
class RebalanceLine:
    """Current-vs-target drift and simulated notional for one target key."""

    asset_id: UUID | None
    current_value: float
    target_value: float
    current_weight: float
    target_weight: float
    absolute_drift: float
    relative_drift: float | None
    trade_notional: float
    direction: SimulatedTradeDirection


@dataclass(frozen=True, slots=True)
class RebalanceSimulationResult:
    """Deterministic hypothetical rebalance result; never an executable order."""

    total_investable_value: float
    lines: tuple[RebalanceLine, ...]
    current_weight_sum: float
    target_weight_sum: float


@dataclass(frozen=True, slots=True)
class RebalanceRuleEvaluation:
    """Current-time rule evaluation independent of historical backtesting."""

    threshold: float | None
    threshold_triggered: bool | None
    schedule: RebalanceSchedule | None
    previous_rebalance_date: date | None
    decision_date: date
    schedule_due: bool | None
