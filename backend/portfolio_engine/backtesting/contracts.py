"""Framework-independent contracts for deterministic Phase 6 backtesting.

Development guide references: Sections 14, 17.1-17.2, 19.6, and 20.2-20.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

BACKTEST_METHOD_VERSION = "1.0"


class BacktestErrorCode(StrEnum):
    """Stable quantitative-engine backtesting failure categories."""

    INVALID_INPUT = "INVALID_INPUT"
    INVALID_PRICE_HISTORY = "INVALID_PRICE_HISTORY"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_ORDER = "INVALID_ORDER"
    INSUFFICIENT_POSITION = "INSUFFICIENT_POSITION"
    NEGATIVE_CASH = "NEGATIVE_CASH"
    NONPOSITIVE_PORTFOLIO_VALUE = "NONPOSITIVE_PORTFOLIO_VALUE"


class BacktestError(ValueError):
    """Typed deterministic backtesting failure."""

    def __init__(self, code: BacktestErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class BacktestWarningCode(StrEnum):
    INCOMPLETE_DATE_INTERSECTION = "INCOMPLETE_DATE_INTERSECTION"
    BUY_SCALED_TO_AVAILABLE_CASH = "BUY_SCALED_TO_AVAILABLE_CASH"
    UNEXECUTED_FINAL_ORDERS = "UNEXECUTED_FINAL_ORDERS"


@dataclass(frozen=True, slots=True)
class BacktestInitialPosition:
    asset_id: UUID
    quantity: float


@dataclass(frozen=True, slots=True)
class PositionQuantity:
    asset_id: UUID
    quantity: float


@dataclass(frozen=True, slots=True)
class PortfolioLedgerState:
    """Long-only quantity/cash state independent of valuation date."""

    positions: tuple[PositionQuantity, ...]
    cash: float


@dataclass(frozen=True, slots=True)
class PortfolioPositionSnapshot:
    asset_id: UUID
    quantity: float
    market_value: float
    weight: float


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Immutable valued portfolio state visible to a strategy at one date."""

    as_of: date
    positions: tuple[PortfolioPositionSnapshot, ...]
    cash: float
    cash_weight: float
    total_value: float


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Normalized strategy output. Execution owns fill conversion."""

    asset_id: UUID
    side: OrderSide
    quantity: float


@dataclass(frozen=True, slots=True)
class BacktestDecision:
    decision_date: date
    orders: tuple[OrderIntent, ...]


@dataclass(frozen=True, slots=True)
class SimulatedFill:
    asset_id: UUID
    side: OrderSide
    quantity: float
    reference_price: float
    fill_price: float
    fill_notional: float
    commission_cost: float
    slippage_cost: float


@dataclass(frozen=True, slots=True)
class BacktestExecutionEvent:
    decision_date: date
    execution_date: date
    orders: tuple[OrderIntent, ...]
    fills: tuple[SimulatedFill, ...]
    pre_trade_value: float
    post_trade_value: float
    turnover: float
    commission_cost: float
    slippage_cost: float
    total_cost: float
    buy_scale: float


@dataclass(frozen=True, slots=True)
class BacktestEquityObservation:
    trade_date: date
    portfolio_value: float


@dataclass(frozen=True, slots=True)
class BacktestReturnObservation:
    trade_date: date
    simple_return: float


@dataclass(frozen=True, slots=True)
class BacktestCostObservation:
    execution_date: date
    commission_cost: float
    slippage_cost: float
    total_cost: float


@dataclass(frozen=True, slots=True)
class BacktestWarning:
    code: BacktestWarningCode
    message: str


@dataclass(frozen=True, slots=True)
class BacktestAssumptions:
    price_field: str
    execution_timing: str
    commission_rate: float
    slippage_rate: float
    turnover_convention: str
    fractional_shares: bool
    long_only: bool
    leverage: bool


@dataclass(frozen=True, slots=True)
class BacktestDataProvenance:
    """Application-supplied market-data identity retained by the pure engine."""

    provider: str
    retrieved_at: datetime | None = None
    data_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class BacktestProvenance:
    provider: str
    retrieved_at: datetime | None
    data_fingerprint: str | None
    requested_period_start: date
    requested_period_end_exclusive: date
    aligned_period_start: date
    aligned_period_end: date
    engine_version: str
    backtest_method_version: str
    strategy_name: str
    strategy_version: str


@dataclass(frozen=True, slots=True)
class BacktestResult:
    aligned_dates: tuple[date, ...]
    snapshots: tuple[PortfolioState, ...]
    equity_curve: tuple[BacktestEquityObservation, ...]
    returns: tuple[BacktestReturnObservation, ...]
    decisions: tuple[BacktestDecision, ...]
    executions: tuple[BacktestExecutionEvent, ...]
    costs: tuple[BacktestCostObservation, ...]
    initial_value: float
    ending_value: float
    cumulative_return: float
    trade_count: int
    turnover: float
    commission_cost: float
    slippage_cost: float
    total_cost: float
    assumptions: BacktestAssumptions
    provenance: BacktestProvenance
    warnings: tuple[BacktestWarning, ...]
