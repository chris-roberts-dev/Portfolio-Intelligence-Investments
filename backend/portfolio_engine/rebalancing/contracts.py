"""Framework-independent contracts for Phase 5 rebalancing calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

REBALANCING_METHOD_VERSION = "1.0"


class RebalancingErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_TARGET_WEIGHTS = "INVALID_TARGET_WEIGHTS"
    INVALID_CURRENT_VALUES = "INVALID_CURRENT_VALUES"
    INVALID_PRICE_HISTORY = "INVALID_PRICE_HISTORY"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_COST_ASSUMPTION = "INVALID_COST_ASSUMPTION"
    NEGATIVE_CASH = "NEGATIVE_CASH"


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


class HistoricalRebalanceTrigger(StrEnum):
    SCHEDULE = "SCHEDULE"
    THRESHOLD = "THRESHOLD"


class HistoricalRebalanceWarningCode(StrEnum):
    INCOMPLETE_DATE_INTERSECTION = "INCOMPLETE_DATE_INTERSECTION"
    UNEXECUTED_FINAL_DECISION = "UNEXECUTED_FINAL_DECISION"


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


@dataclass(frozen=True, slots=True)
class HistoricalPosition:
    """One initial long-only quantity for a historical rebalancing comparison."""

    asset_id: UUID
    quantity: float


@dataclass(frozen=True, slots=True)
class HistoricalRebalancePolicy:
    """One historical schedule or drift-threshold rebalance policy."""

    name: str
    schedule: RebalanceSchedule | None = None
    threshold: float | None = None


@dataclass(frozen=True, slots=True)
class HistoricalRebalanceWarning:
    """Structured non-fatal diagnostic produced by historical simulation."""

    code: HistoricalRebalanceWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class HistoricalAllocationLine:
    """End-of-observation allocation and drift for one target/current identity."""

    asset_id: UUID | None
    market_value: float
    weight: float
    target_weight: float
    absolute_drift: float
    relative_drift: float | None


@dataclass(frozen=True, slots=True)
class HistoricalPortfolioSnapshot:
    """Portfolio value and allocation observed at one common market date."""

    trade_date: date
    total_value: float
    cash_value: float
    period_return: float | None
    lines: tuple[HistoricalAllocationLine, ...]


@dataclass(frozen=True, slots=True)
class HistoricalRebalanceTrade:
    """One simulated fill produced by a historical rebalance execution."""

    asset_id: UUID
    direction: SimulatedTradeDirection
    quantity: float
    reference_price: float
    fill_price: float
    fill_notional: float
    commission_cost: float
    slippage_cost: float


@dataclass(frozen=True, slots=True)
class HistoricalRebalanceEvent:
    """One observable-at-t decision executed on the next common market date."""

    trigger: HistoricalRebalanceTrigger
    decision_date: date
    execution_date: date
    decision_lines: tuple[RebalanceLine, ...]
    pre_trade_value: float
    post_trade_value: float
    turnover: float
    commission_cost: float
    slippage_cost: float
    trades: tuple[HistoricalRebalanceTrade, ...]


@dataclass(frozen=True, slots=True)
class HistoricalRebalancePolicyResult:
    """Historical state evolution and performance summary for one policy."""

    policy: HistoricalRebalancePolicy
    snapshots: tuple[HistoricalPortfolioSnapshot, ...]
    events: tuple[HistoricalRebalanceEvent, ...]
    initial_value: float
    ending_value: float
    cumulative_return: float
    rebalance_count: int
    trade_count: int
    maximum_absolute_drift: float
    turnover: float
    commission_cost: float
    slippage_cost: float
    total_cost: float
    warnings: tuple[HistoricalRebalanceWarning, ...]


@dataclass(frozen=True, slots=True)
class HistoricalRebalanceComparisonResult:
    """Deterministic comparison of historical schedule/threshold policies."""

    period_start: date
    period_end: date
    aligned_dates: tuple[date, ...]
    target_weights: tuple[TargetWeight, ...]
    initial_positions: tuple[HistoricalPosition, ...]
    initial_cash: float
    commission_rate: float
    slippage_rate: float
    turnover_convention: str
    policy_results: tuple[HistoricalRebalancePolicyResult, ...]
    warnings: tuple[HistoricalRebalanceWarning, ...]
