"""Owner-scoped persisted Phase 6 buy-and-hold backtest application service.

Development guide references: Sections 4.3, 9.6-9.7, 14, 15.2-15.3,
17.1-17.2, 19.6, 20.2, and 23.7.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.backtesting.models import (
    BacktestRun,
    BacktestRunStatus,
    BacktestStrategyName,
)
from apps.market_data.contracts import (
    MarketBarQueryError,
    MarketBarStatus,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import MarketBarOrchestrationError
from apps.portfolios.services.current_valuation import MarketBarQueryExecutor
from portfolio_engine.backtesting import (
    BACKTEST_METHOD_VERSION,
    BacktestDataProvenance,
    BacktestError,
    BacktestErrorCode,
    BacktestResult,
    run_backtest,
)
from portfolio_engine.config import (
    DEFAULT_COMMISSION_RATE,
    DEFAULT_SLIPPAGE_RATE,
    MAX_BAR_QUERY_SYMBOLS,
    WEIGHT_SUM_TOLERANCE,
)
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.strategies import (
    BUY_AND_HOLD_STRATEGY_VERSION,
    BuyAndHoldStrategy,
    BuyAndHoldTargetWeight,
)
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


class BacktestApplicationFailureCode(StrEnum):
    """Stable auditable failure codes for persisted backtest runs."""

    ASSET_UNSUPPORTED = "ASSET_UNSUPPORTED"
    MARKET_DATA_UNAVAILABLE = "MARKET_DATA_UNAVAILABLE"
    BACKTEST_INVALID_INPUT = "BACKTEST_INVALID_INPUT"
    BACKTEST_INVALID_PRICE_HISTORY = "BACKTEST_INVALID_PRICE_HISTORY"
    BACKTEST_INSUFFICIENT_HISTORY = "BACKTEST_INSUFFICIENT_HISTORY"
    BACKTEST_INVALID_ORDER = "BACKTEST_INVALID_ORDER"
    BACKTEST_INSUFFICIENT_POSITION = "BACKTEST_INSUFFICIENT_POSITION"
    BACKTEST_NEGATIVE_CASH = "BACKTEST_NEGATIVE_CASH"
    BACKTEST_NONPOSITIVE_PORTFOLIO_VALUE = "BACKTEST_NONPOSITIVE_PORTFOLIO_VALUE"
    BACKTEST_EXECUTION_FAILED = "BACKTEST_EXECUTION_FAILED"


@dataclass(frozen=True, slots=True)
class BacktestTargetWeightInput:
    asset_id: UUID
    weight: float


@dataclass(frozen=True, slots=True)
class CreateBacktestRunCommand:
    strategy: BacktestStrategyName
    period_start: date
    period_end_exclusive: date
    initial_cash: float
    target_weights: tuple[BacktestTargetWeightInput, ...]
    commission_rate: float = DEFAULT_COMMISSION_RATE
    slippage_rate: float = DEFAULT_SLIPPAGE_RATE


class BacktestApplicationError(ValueError):
    """Raised for invalid requests that fail before persistence begins."""


class BacktestRunDomainFailure(ValueError):
    """Expected auditable failure after a persisted run has been created."""

    def __init__(self, code: BacktestApplicationFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def create_backtest_run(
    *,
    user: User,
    command: CreateBacktestRunCommand,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> BacktestRun:
    """Create, execute, and persist one synchronous owner-scoped buy-and-hold run."""
    normalized_weights = _normalize_command(command)
    normalized_initial_cash = _normalized_decimal(
        command.initial_cash,
        quantum=Decimal("0.00000001"),
        field_name="initial_cash",
    )
    normalized_commission = _normalized_decimal(
        command.commission_rate,
        quantum=Decimal("0.000000000001"),
        field_name="commission_rate",
    )
    normalized_slippage = _normalized_decimal(
        command.slippage_rate,
        quantum=Decimal("0.000000000001"),
        field_name="slippage_rate",
    )
    if normalized_initial_cash <= Decimal("0"):
        raise BacktestApplicationError("initial_cash must remain positive at persisted precision.")
    normalized_provider = provider_name.strip().lower()
    if not normalized_provider:
        raise BacktestApplicationError("provider_name must not be blank.")

    included_asset_ids = tuple(item.asset_id for item in normalized_weights)
    run = BacktestRun.objects.create(
        user=user,
        status=BacktestRunStatus.PENDING,
        strategy=command.strategy,
        period_start=command.period_start,
        period_end_exclusive=command.period_end_exclusive,
        provider=normalized_provider,
        price_field="adjusted_close",
        included_asset_ids=[str(asset_id) for asset_id in included_asset_ids],
        parameters=_parameters_json(normalized_weights),
        initial_cash=normalized_initial_cash,
        commission_rate=normalized_commission,
        slippage_rate=normalized_slippage,
        engine_version=PORTFOLIO_ENGINE_VERSION,
        method_version=BACKTEST_METHOD_VERSION,
        strategy_version=BUY_AND_HOLD_STRATEGY_VERSION,
    )
    _transition_running(run)
    failure_retrieved_at: datetime | None = None
    failure_fingerprint = ""

    try:
        assets = _load_eligible_assets(included_asset_ids)
        frames, retrieved_at = _load_price_frames(
            assets=assets,
            period_start=command.period_start,
            period_end_exclusive=command.period_end_exclusive,
            provider_name=normalized_provider,
            resolver=resolver,
            provider=provider,
            executor=executor,
        )
        failure_retrieved_at = retrieved_at
        strategy = BuyAndHoldStrategy(
            targets=tuple(
                BuyAndHoldTargetWeight(asset_id=item.asset_id, weight=item.weight)
                for item in normalized_weights
            )
        )
        fingerprint = _data_fingerprint(asset_ids=included_asset_ids, frames=frames)
        failure_fingerprint = fingerprint
        result = run_backtest(
            price_frames=frames,
            initial_positions=(),
            initial_cash=float(normalized_initial_cash),
            strategy=strategy,
            requested_period_start=command.period_start,
            requested_period_end_exclusive=command.period_end_exclusive,
            data_provenance=BacktestDataProvenance(
                provider=normalized_provider,
                retrieved_at=retrieved_at,
                data_fingerprint=fingerprint,
            ),
            commission_rate=float(normalized_commission),
            slippage_rate=float(normalized_slippage),
        )
    except BacktestRunDomainFailure as exc:
        return _transition_failed(run, code=exc.code, message=str(exc))
    except BacktestError as exc:
        return _transition_failed(
            run,
            code=_application_code_for_engine_error(exc),
            message=str(exc),
            data_retrieved_at=failure_retrieved_at,
            data_fingerprint=failure_fingerprint,
        )
    except (MarketBarQueryError, MarketBarOrchestrationError) as exc:
        return _transition_failed(
            run,
            code=BacktestApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
            message=str(exc),
        )
    except Exception:
        _transition_failed(
            run,
            code=BacktestApplicationFailureCode.BACKTEST_EXECUTION_FAILED,
            message="Unexpected backtest execution failure.",
            data_retrieved_at=failure_retrieved_at,
            data_fingerprint=failure_fingerprint,
        )
        raise

    return _transition_succeeded(
        run,
        result=result,
        data_retrieved_at=retrieved_at,
        data_fingerprint=fingerprint,
    )


def _normalize_command(
    command: CreateBacktestRunCommand,
) -> tuple[BacktestTargetWeightInput, ...]:
    if command.strategy != BacktestStrategyName.BUY_AND_HOLD:
        raise BacktestApplicationError("Only BUY_AND_HOLD is implemented in this Phase 6 batch.")
    if command.period_start >= command.period_end_exclusive:
        raise BacktestApplicationError("period_end_exclusive must be later than period_start.")
    if not math.isfinite(command.initial_cash) or command.initial_cash <= 0.0:
        raise BacktestApplicationError("initial_cash must be finite and positive.")
    _unit_rate(command.commission_rate, "commission_rate")
    _unit_rate(command.slippage_rate, "slippage_rate")

    if not command.target_weights:
        raise BacktestApplicationError("BUY_AND_HOLD requires target_weights.")
    if len(command.target_weights) > MAX_BAR_QUERY_SYMBOLS:
        raise BacktestApplicationError(
            f"No more than {MAX_BAR_QUERY_SYMBOLS} target weights may be supplied."
        )

    seen: set[UUID] = set()
    normalized: list[BacktestTargetWeightInput] = []
    for index, item in enumerate(command.target_weights):
        if item.asset_id in seen:
            raise BacktestApplicationError(
                f"target_weights contains duplicate asset at index {index}."
            )
        seen.add(item.asset_id)
        if not math.isfinite(item.weight) or item.weight < 0.0 or item.weight > 1.0:
            raise BacktestApplicationError(
                "Target weights must be finite and between zero and one."
            )
        normalized.append(
            BacktestTargetWeightInput(asset_id=item.asset_id, weight=float(item.weight))
        )

    total = math.fsum(item.weight for item in normalized)
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise BacktestApplicationError("Target weights must sum to one within tolerance.")
    return tuple(sorted(normalized, key=lambda item: str(item.asset_id)))


def _normalized_decimal(
    value: float,
    *,
    quantum: Decimal,
    field_name: str,
) -> Decimal:
    if not math.isfinite(value):
        raise BacktestApplicationError(f"{field_name} must be finite.")
    return Decimal(str(value)).quantize(quantum)


def _unit_rate(value: float, field_name: str) -> None:
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise BacktestApplicationError(f"{field_name} must be finite and between zero and one.")


def _load_eligible_assets(asset_ids: Sequence[UUID]) -> dict[UUID, Asset]:
    assets = Asset.objects.in_bulk(asset_ids)
    for asset_id in asset_ids:
        asset = assets.get(asset_id)
        if (
            asset is None
            or not asset.is_active
            or asset.currency != "USD"
            or asset.asset_type not in (AssetType.STOCK, AssetType.ETF)
        ):
            raise BacktestRunDomainFailure(
                BacktestApplicationFailureCode.ASSET_UNSUPPORTED,
                f"Asset {asset_id} is not an active supported USD stock/ETF.",
            )
    return assets


def _load_price_frames(
    *,
    assets: Mapping[UUID, Asset],
    period_start: date,
    period_end_exclusive: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> tuple[dict[UUID, PriceFrame], datetime]:
    asset_ids = tuple(assets)
    symbols = tuple(assets[asset_id].symbol for asset_id in asset_ids)
    if len(set(symbols)) != len(symbols):
        raise BacktestRunDomainFailure(
            BacktestApplicationFailureCode.ASSET_UNSUPPORTED,
            "Backtest assets must have unique canonical symbols.",
        )

    query = normalize_market_bar_query(
        symbols,
        start=period_start,
        end=period_end_exclusive,
        provider=provider_name,
    )
    batch = executor(query, resolver=resolver, provider=provider)
    if batch.meta.provider.strip().lower() != provider_name:
        raise BacktestRunDomainFailure(
            BacktestApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
            "Backtest market-data provider provenance does not match the requested provider.",
        )

    by_symbol = {result.symbol: result for result in batch.results}
    frames: dict[UUID, PriceFrame] = {}
    for asset_id in asset_ids:
        asset = assets[asset_id]
        symbol_result = by_symbol.get(asset.symbol)
        if symbol_result is None or symbol_result.status is not MarketBarStatus.SUCCEEDED:
            symbol_status = symbol_result.status if symbol_result is not None else "MISSING"
            raise BacktestRunDomainFailure(
                BacktestApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
                f"Backtest market data is unavailable for {asset.symbol}: {symbol_status}.",
            )
        if symbol_result.asset_id != asset_id:
            raise BacktestRunDomainFailure(
                BacktestApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
                f"Backtest market data identity mismatch for {asset.symbol}.",
            )
        if not symbol_result.bars:
            raise BacktestRunDomainFailure(
                BacktestApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
                f"Backtest market data is empty for {asset.symbol}.",
            )
        frames[asset_id] = symbol_result.bars

    return frames, batch.meta.retrieved_at


def _parameters_json(
    target_weights: Sequence[BacktestTargetWeightInput],
) -> dict[str, object]:
    return {
        "target_weights": [
            {"asset_id": str(item.asset_id), "weight": item.weight} for item in target_weights
        ],
        "minimum_history_observations": 1,
        "initial_allocation_semantics": (
            "observe_first_aligned_close_then_execute_target_buys_at_next_aligned_adjusted_close"
        ),
        "rebalance_after_initial_execution": False,
    }


def _transition_running(run: BacktestRun) -> None:
    run.status = BacktestRunStatus.RUNNING
    run.started_at = timezone.now()
    run.full_clean()
    run.save(update_fields=("status", "started_at", "updated_at"))


def _transition_succeeded(
    run: BacktestRun,
    *,
    result: BacktestResult,
    data_retrieved_at: datetime,
    data_fingerprint: str,
) -> BacktestRun:
    serialized = _serialize_result(result)
    warnings = serialized["warnings"]
    assert isinstance(warnings, list)
    with transaction.atomic():
        run.status = BacktestRunStatus.SUCCEEDED
        run.result = serialized
        run.warnings = warnings
        run.data_retrieved_at = data_retrieved_at
        run.data_fingerprint = data_fingerprint
        run.completed_at = timezone.now()
        run.failure_code = ""
        run.failure_message = ""
        run.full_clean()
        run.save()
    return run


def _transition_failed(
    run: BacktestRun,
    *,
    code: BacktestApplicationFailureCode,
    message: str,
    data_retrieved_at: datetime | None = None,
    data_fingerprint: str = "",
) -> BacktestRun:
    with transaction.atomic():
        run.status = BacktestRunStatus.FAILED
        run.result = None
        run.warnings = []
        run.data_retrieved_at = data_retrieved_at
        run.data_fingerprint = data_fingerprint
        run.failure_code = code.value
        run.failure_message = message
        run.completed_at = timezone.now()
        run.full_clean()
        run.save()
    return run


def _application_code_for_engine_error(exc: BacktestError) -> BacktestApplicationFailureCode:
    mapping = {
        BacktestErrorCode.INVALID_INPUT: BacktestApplicationFailureCode.BACKTEST_INVALID_INPUT,
        BacktestErrorCode.INVALID_PRICE_HISTORY: (
            BacktestApplicationFailureCode.BACKTEST_INVALID_PRICE_HISTORY
        ),
        BacktestErrorCode.INSUFFICIENT_HISTORY: (
            BacktestApplicationFailureCode.BACKTEST_INSUFFICIENT_HISTORY
        ),
        BacktestErrorCode.INVALID_ORDER: BacktestApplicationFailureCode.BACKTEST_INVALID_ORDER,
        BacktestErrorCode.INSUFFICIENT_POSITION: (
            BacktestApplicationFailureCode.BACKTEST_INSUFFICIENT_POSITION
        ),
        BacktestErrorCode.NEGATIVE_CASH: BacktestApplicationFailureCode.BACKTEST_NEGATIVE_CASH,
        BacktestErrorCode.NONPOSITIVE_PORTFOLIO_VALUE: (
            BacktestApplicationFailureCode.BACKTEST_NONPOSITIVE_PORTFOLIO_VALUE
        ),
    }
    return mapping[exc.code]


def _data_fingerprint(
    *,
    asset_ids: Sequence[UUID],
    frames: Mapping[UUID, PriceFrame],
) -> str:
    rows: list[str] = []
    for asset_id in asset_ids:
        for bar in frames[asset_id]:
            if bar.adjusted_close is not None:
                rows.append(
                    f"{asset_id}|{bar.trade_date.isoformat()}|{float(bar.adjusted_close):.17g}"
                )
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _serialize_result(result: BacktestResult) -> dict[str, object]:
    return {
        "aligned_dates": [value.isoformat() for value in result.aligned_dates],
        "snapshots": [
            {
                "as_of": snapshot.as_of.isoformat(),
                "positions": [
                    {
                        "asset_id": str(position.asset_id),
                        "quantity": position.quantity,
                        "market_value": position.market_value,
                        "weight": position.weight,
                    }
                    for position in snapshot.positions
                ],
                "cash": snapshot.cash,
                "cash_weight": snapshot.cash_weight,
                "total_value": snapshot.total_value,
            }
            for snapshot in result.snapshots
        ],
        "equity_curve": [
            {"trade_date": point.trade_date.isoformat(), "portfolio_value": point.portfolio_value}
            for point in result.equity_curve
        ],
        "returns": [
            {"trade_date": point.trade_date.isoformat(), "simple_return": point.simple_return}
            for point in result.returns
        ],
        "decisions": [
            {
                "decision_date": decision.decision_date.isoformat(),
                "orders": [
                    {
                        "asset_id": str(order.asset_id),
                        "side": order.side.value,
                        "quantity": order.quantity,
                    }
                    for order in decision.orders
                ],
            }
            for decision in result.decisions
        ],
        "executions": [
            {
                "decision_date": event.decision_date.isoformat(),
                "execution_date": event.execution_date.isoformat(),
                "orders": [
                    {
                        "asset_id": str(order.asset_id),
                        "side": order.side.value,
                        "quantity": order.quantity,
                    }
                    for order in event.orders
                ],
                "fills": [
                    {
                        "asset_id": str(fill.asset_id),
                        "side": fill.side.value,
                        "quantity": fill.quantity,
                        "reference_price": fill.reference_price,
                        "fill_price": fill.fill_price,
                        "fill_notional": fill.fill_notional,
                        "commission_cost": fill.commission_cost,
                        "slippage_cost": fill.slippage_cost,
                    }
                    for fill in event.fills
                ],
                "pre_trade_value": event.pre_trade_value,
                "post_trade_value": event.post_trade_value,
                "turnover": event.turnover,
                "commission_cost": event.commission_cost,
                "slippage_cost": event.slippage_cost,
                "total_cost": event.total_cost,
                "buy_scale": event.buy_scale,
            }
            for event in result.executions
        ],
        "costs": [
            {
                "execution_date": point.execution_date.isoformat(),
                "commission_cost": point.commission_cost,
                "slippage_cost": point.slippage_cost,
                "total_cost": point.total_cost,
            }
            for point in result.costs
        ],
        "summary": {
            "initial_value": result.initial_value,
            "ending_value": result.ending_value,
            "cumulative_return": result.cumulative_return,
            "trade_count": result.trade_count,
            "turnover": result.turnover,
            "commission_cost": result.commission_cost,
            "slippage_cost": result.slippage_cost,
            "total_cost": result.total_cost,
        },
        "assumptions": {
            "price_field": result.assumptions.price_field,
            "execution_timing": result.assumptions.execution_timing,
            "commission_rate": result.assumptions.commission_rate,
            "slippage_rate": result.assumptions.slippage_rate,
            "turnover_convention": result.assumptions.turnover_convention,
            "fractional_shares": result.assumptions.fractional_shares,
            "long_only": result.assumptions.long_only,
            "leverage": result.assumptions.leverage,
        },
        "provenance": {
            "provider": result.provenance.provider,
            "retrieved_at": (
                result.provenance.retrieved_at.isoformat()
                if result.provenance.retrieved_at is not None
                else None
            ),
            "data_fingerprint": result.provenance.data_fingerprint,
            "requested_period_start": result.provenance.requested_period_start.isoformat(),
            "requested_period_end_exclusive": (
                result.provenance.requested_period_end_exclusive.isoformat()
            ),
            "aligned_period_start": result.provenance.aligned_period_start.isoformat(),
            "aligned_period_end": result.provenance.aligned_period_end.isoformat(),
            "engine_version": result.provenance.engine_version,
            "backtest_method_version": result.provenance.backtest_method_version,
            "strategy_name": result.provenance.strategy_name,
            "strategy_version": result.provenance.strategy_version,
        },
        "warnings": [
            {"code": warning.code.value, "message": warning.message} for warning in result.warnings
        ],
    }
