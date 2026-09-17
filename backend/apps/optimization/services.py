"""Owner-scoped persisted optimization-run application service.

Development guide references: Sections 4.3, 12, 15.6, and 17.2.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.contracts import MarketBarStatus, normalize_market_bar_query
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.optimization.models import (
    OptimizationRun,
    OptimizationRunMethod,
    OptimizationRunSource,
    OptimizationRunStatus,
)
from apps.portfolios.models import Portfolio
from apps.portfolios.services.current_valuation import MarketBarQueryExecutor
from apps.portfolios.services.ledger import replay_portfolio_ledger
from portfolio_engine.config import TRADING_DAYS_PER_YEAR, WEIGHT_SUM_TOLERANCE
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.optimization import (
    OptimizationError,
    OptimizationProblem,
    WeightBound,
    build_problem,
    efficient_frontier,
    equal_weight_portfolio,
    estimate_historical_inputs,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
)
from portfolio_engine.optimization.contracts import (
    OPTIMIZATION_METHOD_VERSION,
    OptimizedPortfolio,
)
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


class OptimizationApplicationFailureCode(StrEnum):
    """Stable persisted application failure codes for optimization runs."""

    NO_ELIGIBLE_ASSETS = "NO_ELIGIBLE_ASSETS"
    ASSET_NOT_HELD = "ASSET_NOT_HELD"
    ASSET_UNSUPPORTED = "ASSET_UNSUPPORTED"
    MARKET_DATA_UNAVAILABLE = "MARKET_DATA_UNAVAILABLE"
    OPTIMIZATION_INVALID_INPUT = "OPTIMIZATION_INVALID_INPUT"
    OPTIMIZATION_INSUFFICIENT_DATA = "OPTIMIZATION_INSUFFICIENT_DATA"
    OPTIMIZATION_INFEASIBLE = "OPTIMIZATION_INFEASIBLE"
    OPTIMIZATION_SINGULAR_COVARIANCE = "OPTIMIZATION_SINGULAR_COVARIANCE"
    OPTIMIZATION_SOLVER_FAILED = "OPTIMIZATION_SOLVER_FAILED"
    OPTIMIZATION_POST_VALIDATION_FAILED = "OPTIMIZATION_POST_VALIDATION_FAILED"
    OPTIMIZATION_DEGENERATE_RETURN_RANGE = "OPTIMIZATION_DEGENERATE_RETURN_RANGE"


@dataclass(frozen=True, slots=True)
class AssetWeightBounds:
    """Optional custom bound override for one canonical asset."""

    asset_id: UUID
    minimum: float
    maximum: float


@dataclass(frozen=True, slots=True)
class BaselineWeight:
    """One optional user-supplied reference allocation weight."""

    asset_id: UUID
    weight: float


@dataclass(frozen=True, slots=True)
class CreateOptimizationRunCommand:
    """Validated application command for one synchronous persisted run."""

    portfolio_id: UUID | None
    method: OptimizationRunMethod
    period_start: date
    period_end: date
    source_type: OptimizationRunSource = OptimizationRunSource.PORTFOLIO
    requested_asset_ids: tuple[UUID, ...] | None = None
    bounds: tuple[AssetWeightBounds, ...] = ()
    baseline_weights: tuple[BaselineWeight, ...] = ()
    risk_free_rate_annual: float = 0.0
    frontier_points: int = 25


class OptimizationApplicationError(ValueError):
    """Raised for request conditions that should fail before a run is created."""


def create_optimization_run(
    *,
    user: User,
    command: CreateOptimizationRunCommand,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> OptimizationRun:
    """Create, execute, and persist one portfolio or ad hoc optimization run."""
    _validate_command(command)

    portfolio: Portfolio | None = None
    held_asset_ids: tuple[UUID, ...] = ()

    if command.source_type is OptimizationRunSource.PORTFOLIO:
        assert command.portfolio_id is not None
        portfolio = (
            Portfolio.objects.owned_by(user)
            .select_related("benchmark_asset")
            .get(id=command.portfolio_id)
        )
        as_of = datetime.combine(command.period_end, time.min, tzinfo=UTC) - timedelta(
            microseconds=1
        )
        ledger = replay_portfolio_ledger(portfolio, as_of=as_of)
        held_asset_ids = tuple(
            position.asset_id for position in ledger.positions if position.quantity > 0
        )
        selected_asset_ids = _selected_portfolio_asset_ids(
            held_asset_ids=held_asset_ids,
            requested_asset_ids=command.requested_asset_ids,
        )
    else:
        assert command.requested_asset_ids is not None
        selected_asset_ids = command.requested_asset_ids

    _validate_baseline_weights(
        selected_asset_ids=selected_asset_ids,
        baseline_weights=command.baseline_weights,
    )

    run = OptimizationRun.objects.create(
        user=user,
        source_type=command.source_type,
        portfolio=portfolio,
        benchmark_asset=(portfolio.benchmark_asset if portfolio is not None else None),
        status=OptimizationRunStatus.PENDING,
        method=command.method,
        period_start=command.period_start,
        period_end=command.period_end,
        provider=provider_name,
        price_field="adjusted_close",
        annualization_factor=TRADING_DAYS_PER_YEAR,
        risk_free_rate_annual=Decimal(str(command.risk_free_rate_annual)),
        included_asset_ids=[str(asset_id) for asset_id in selected_asset_ids],
        baseline_weights=[
            {"asset_id": str(item.asset_id), "weight": item.weight}
            for item in command.baseline_weights
        ],
        parameters=_parameters_json(command),
        engine_version=PORTFOLIO_ENGINE_VERSION,
        method_version=OPTIMIZATION_METHOD_VERSION,
    )
    _transition_running(run)

    try:
        assets = _load_eligible_assets(selected_asset_ids)
        frames, retrieved_at = _load_price_frames(
            assets=assets,
            period_start=command.period_start,
            period_end=command.period_end,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            executor=executor,
        )
        estimate = estimate_historical_inputs(
            tuple(str(asset_id) for asset_id in selected_asset_ids),
            frames,
        )
        problem = build_problem(
            asset_keys=estimate.asset_keys,
            expected_returns=estimate.expected_returns,
            covariance=estimate.covariance,
            bounds=_engine_bounds(selected_asset_ids, command.bounds),
            risk_free_rate_annual=command.risk_free_rate_annual,
        )
        result = _execute_method(
            method=command.method,
            problem=problem,
            frontier_points=command.frontier_points,
        )
        fingerprint = _data_fingerprint(
            asset_ids=selected_asset_ids,
            frames=frames,
        )
    except OptimizationRunDomainFailure as exc:
        return _transition_failed(run, code=exc.code, message=str(exc))
    except OptimizationError as exc:
        return _transition_failed(
            run,
            code=_application_code_for_engine_error(exc),
            message=str(exc),
        )
    except Exception:
        _transition_failed(
            run,
            code=OptimizationApplicationFailureCode.OPTIMIZATION_SOLVER_FAILED,
            message="Unexpected optimization execution failure.",
        )
        raise

    return _transition_succeeded(
        run,
        result=result,
        observations=estimate.observations,
        covariance_rank=estimate.covariance_rank,
        data_retrieved_at=retrieved_at,
        data_fingerprint=fingerprint,
    )


class OptimizationRunDomainFailure(ValueError):
    """Expected auditable optimization-run failure after persistence begins."""

    def __init__(self, code: OptimizationApplicationFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validate_command(command: CreateOptimizationRunCommand) -> None:
    if command.period_end <= command.period_start:
        raise OptimizationApplicationError("period_end must be later than period_start.")

    if not math.isfinite(command.risk_free_rate_annual):
        raise OptimizationApplicationError("risk_free_rate_annual must be finite.")

    if command.frontier_points < 2 or command.frontier_points > 100:
        raise OptimizationApplicationError("frontier_points must be between 2 and 100.")

    if command.source_type is OptimizationRunSource.PORTFOLIO:
        if command.portfolio_id is None:
            raise OptimizationApplicationError("Portfolio-scoped runs require portfolio_id.")
    elif command.source_type is OptimizationRunSource.AD_HOC:
        if command.portfolio_id is not None:
            raise OptimizationApplicationError("Ad hoc runs cannot include portfolio_id.")
        if not command.requested_asset_ids:
            raise OptimizationApplicationError(
                "Ad hoc runs require an explicit non-empty asset_ids universe."
            )

    if command.requested_asset_ids is not None and not command.requested_asset_ids:
        raise OptimizationApplicationError("asset_ids must not be empty when supplied.")

    if command.requested_asset_ids is not None and (
        len(set(command.requested_asset_ids)) != len(command.requested_asset_ids)
    ):
        raise OptimizationApplicationError("asset_ids must be unique.")

    bound_asset_ids = tuple(bound.asset_id for bound in command.bounds)
    if len(set(bound_asset_ids)) != len(bound_asset_ids):
        raise OptimizationApplicationError("bounds must contain each asset at most once.")

    for bound in command.bounds:
        if (
            not math.isfinite(bound.minimum)
            or not math.isfinite(bound.maximum)
            or bound.minimum < 0.0
            or bound.maximum > 1.0
            or bound.minimum > bound.maximum
        ):
            raise OptimizationApplicationError(
                "Each bound must satisfy finite 0 <= minimum <= maximum <= 1."
            )


def _validate_baseline_weights(
    *,
    selected_asset_ids: Sequence[UUID],
    baseline_weights: Sequence[BaselineWeight],
) -> None:
    if not baseline_weights:
        return

    baseline_asset_ids = tuple(item.asset_id for item in baseline_weights)
    if len(set(baseline_asset_ids)) != len(baseline_asset_ids):
        raise OptimizationApplicationError("baseline_weights must contain each asset at most once.")

    selected = tuple(selected_asset_ids)
    if set(baseline_asset_ids) != set(selected):
        raise OptimizationApplicationError(
            "A supplied baseline must include exactly every asset in the optimization universe."
        )

    total = 0.0
    for item in baseline_weights:
        if not math.isfinite(item.weight) or item.weight < 0.0 or item.weight > 1.0:
            raise OptimizationApplicationError(
                "Baseline weights must be finite and between zero and one."
            )
        total += item.weight

    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise OptimizationApplicationError(
            "Complete baseline weights must sum to one within tolerance."
        )


def _selected_portfolio_asset_ids(
    *,
    held_asset_ids: tuple[UUID, ...],
    requested_asset_ids: tuple[UUID, ...] | None,
) -> tuple[UUID, ...]:
    if not held_asset_ids:
        raise OptimizationApplicationError(
            "Portfolio has no positive security positions at the requested period end."
        )
    if requested_asset_ids is None:
        return held_asset_ids

    held = set(held_asset_ids)
    missing = tuple(asset_id for asset_id in requested_asset_ids if asset_id not in held)
    if missing:
        raise OptimizationApplicationError(
            f"Requested assets are not positive portfolio holdings: {missing!r}."
        )
    return requested_asset_ids


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
            raise OptimizationRunDomainFailure(
                OptimizationApplicationFailureCode.ASSET_UNSUPPORTED,
                f"Asset {asset_id} is not an active supported USD stock/ETF.",
            )
    return assets


def _load_price_frames(
    *,
    assets: Mapping[UUID, Asset],
    period_start: date,
    period_end: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> tuple[dict[str, PriceFrame], datetime]:
    asset_ids = tuple(assets)
    symbols = tuple(assets[asset_id].symbol for asset_id in asset_ids)
    if len(set(symbols)) != len(symbols):
        raise OptimizationRunDomainFailure(
            OptimizationApplicationFailureCode.ASSET_UNSUPPORTED,
            "Optimization assets must have unique canonical symbols.",
        )

    query = normalize_market_bar_query(
        symbols,
        start=period_start,
        end=period_end,
        provider=provider_name,
    )
    batch = executor(query, resolver=resolver, provider=provider)
    by_symbol = {result.symbol: result for result in batch.results}
    frames: dict[str, PriceFrame] = {}

    for asset_id in asset_ids:
        asset = assets[asset_id]
        symbol_result = by_symbol.get(asset.symbol)
        if symbol_result is None or symbol_result.status != MarketBarStatus.SUCCEEDED:
            symbol_status = symbol_result.status if symbol_result is not None else "MISSING"
            raise OptimizationRunDomainFailure(
                OptimizationApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
                f"Optimization market data is unavailable for {asset.symbol}: {symbol_status}.",
            )
        if not symbol_result.bars:
            raise OptimizationRunDomainFailure(
                OptimizationApplicationFailureCode.MARKET_DATA_UNAVAILABLE,
                f"Optimization market data is empty for {asset.symbol}.",
            )
        frames[str(asset_id)] = symbol_result.bars

    return frames, batch.meta.retrieved_at


def _engine_bounds(
    asset_ids: Sequence[UUID],
    overrides: Sequence[AssetWeightBounds],
) -> tuple[WeightBound, ...]:
    by_asset = {bound.asset_id: bound for bound in overrides}
    unknown = set(by_asset).difference(asset_ids)
    if unknown:
        raise OptimizationRunDomainFailure(
            OptimizationApplicationFailureCode.ASSET_UNSUPPORTED,
            f"Bounds reference assets outside the optimization universe: {tuple(unknown)!r}.",
        )
    return tuple(
        WeightBound(
            minimum=by_asset[asset_id].minimum,
            maximum=by_asset[asset_id].maximum,
        )
        if asset_id in by_asset
        else WeightBound()
        for asset_id in asset_ids
    )


def _execute_method(
    *,
    method: OptimizationRunMethod,
    problem: OptimizationProblem,
    frontier_points: int,
) -> dict[str, object]:
    if method == OptimizationRunMethod.EQUAL_WEIGHT:
        return _single_result_json(equal_weight_portfolio(problem))
    if method == OptimizationRunMethod.MINIMUM_VARIANCE:
        return _single_result_json(minimum_variance_portfolio(problem))
    if method == OptimizationRunMethod.MAXIMUM_SHARPE:
        return _single_result_json(maximum_sharpe_portfolio(problem))
    if method == OptimizationRunMethod.EFFICIENT_FRONTIER:
        frontier = efficient_frontier(problem, points=frontier_points)
        return {
            "portfolio": None,
            "frontier": [_portfolio_json(point) for point in frontier.points],
        }
    raise OptimizationApplicationError(f"Unsupported optimization method: {method}.")


def _single_result_json(portfolio: OptimizedPortfolio) -> dict[str, object]:
    return {"portfolio": _portfolio_json(portfolio), "frontier": []}


def _portfolio_json(portfolio: OptimizedPortfolio) -> dict[str, object]:
    return {
        "method": portfolio.method.value,
        "weights": [
            {"asset_id": asset_key, "weight": weight}
            for asset_key, weight in zip(
                portfolio.asset_keys,
                portfolio.weights,
                strict=True,
            )
        ],
        "expected_return": portfolio.expected_return,
        "expected_volatility": portfolio.expected_volatility,
        "sharpe_ratio": portfolio.sharpe_ratio,
        "target_return": portfolio.target_return,
    }


def _parameters_json(command: CreateOptimizationRunCommand) -> dict[str, object]:
    return {
        "source_type": command.source_type.value,
        "requested_asset_ids": (
            [str(asset_id) for asset_id in command.requested_asset_ids]
            if command.requested_asset_ids is not None
            else None
        ),
        "bounds": [
            {
                "asset_id": str(bound.asset_id),
                "minimum": bound.minimum,
                "maximum": bound.maximum,
            }
            for bound in command.bounds
        ],
        "baseline_weights": [
            {
                "asset_id": str(item.asset_id),
                "weight": item.weight,
            }
            for item in command.baseline_weights
        ],
        "risk_free_rate_annual": command.risk_free_rate_annual,
        "frontier_points": command.frontier_points,
    }


def _transition_running(run: OptimizationRun) -> None:
    run.status = OptimizationRunStatus.RUNNING
    run.started_at = timezone.now()
    run.full_clean()
    run.save(update_fields=("status", "started_at", "updated_at"))


def _transition_succeeded(
    run: OptimizationRun,
    *,
    result: dict[str, object],
    observations: int,
    covariance_rank: int,
    data_retrieved_at: datetime,
    data_fingerprint: str,
) -> OptimizationRun:
    with transaction.atomic():
        run.status = OptimizationRunStatus.SUCCEEDED
        run.result = result
        run.parameters = {
            **run.parameters,
            "observations": observations,
            "covariance_rank": covariance_rank,
        }
        run.data_retrieved_at = data_retrieved_at
        run.data_fingerprint = data_fingerprint
        run.completed_at = timezone.now()
        run.failure_code = ""
        run.failure_message = ""
        run.full_clean()
        run.save()
    return run


def _transition_failed(
    run: OptimizationRun,
    *,
    code: OptimizationApplicationFailureCode,
    message: str,
) -> OptimizationRun:
    with transaction.atomic():
        run.status = OptimizationRunStatus.FAILED
        run.result = None
        run.failure_code = code.value
        run.failure_message = message
        run.completed_at = timezone.now()
        run.full_clean()
        run.save()
    return run


def _application_code_for_engine_error(
    exc: OptimizationError,
) -> OptimizationApplicationFailureCode:
    from portfolio_engine.optimization.contracts import OptimizationErrorCode

    mapping = {
        OptimizationErrorCode.INVALID_INPUT: (
            OptimizationApplicationFailureCode.OPTIMIZATION_INVALID_INPUT
        ),
        OptimizationErrorCode.INSUFFICIENT_DATA: (
            OptimizationApplicationFailureCode.OPTIMIZATION_INSUFFICIENT_DATA
        ),
        OptimizationErrorCode.INFEASIBLE_CONSTRAINTS: (
            OptimizationApplicationFailureCode.OPTIMIZATION_INFEASIBLE
        ),
        OptimizationErrorCode.SINGULAR_COVARIANCE: (
            OptimizationApplicationFailureCode.OPTIMIZATION_SINGULAR_COVARIANCE
        ),
        OptimizationErrorCode.SOLVER_FAILED: (
            OptimizationApplicationFailureCode.OPTIMIZATION_SOLVER_FAILED
        ),
        OptimizationErrorCode.POST_VALIDATION_FAILED: (
            OptimizationApplicationFailureCode.OPTIMIZATION_POST_VALIDATION_FAILED
        ),
        OptimizationErrorCode.DEGENERATE_RETURN_RANGE: (
            OptimizationApplicationFailureCode.OPTIMIZATION_DEGENERATE_RETURN_RANGE
        ),
    }
    return mapping[exc.code]


def _data_fingerprint(
    *,
    asset_ids: Sequence[UUID],
    frames: Mapping[str, PriceFrame],
) -> str:
    rows: list[str] = []
    for asset_id in asset_ids:
        for bar in frames[str(asset_id)]:
            if bar.adjusted_close is not None:
                rows.append(
                    f"{asset_id}|{bar.trade_date.isoformat()}|{float(bar.adjusted_close):.17g}"
                )
    payload = "\n".join(rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
