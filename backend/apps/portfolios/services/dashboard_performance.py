"""Display-ready portfolio performance series for dashboard consumers.

The application service composes the authoritative daily portfolio performance
service with an optional configured benchmark. It does not reimplement ledger
replay or portfolio return mathematics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.market_data.contracts import (
    MarketBarStatus,
    MarketBarSymbolResult,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
    TradingSessionCalendar,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceWarning,
    DailyPerformanceWarningCode,
    DailyPortfolioPerformanceResult,
    DailyPortfolioValuation,
    calculate_owned_portfolio_daily_performance,
)
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION

ZERO = Decimal("0")


class DashboardPerformanceError(ValueError):
    """Raised when a dashboard performance result cannot be assembled safely."""


class PerformanceDataQualityState(StrEnum):
    """Display-ready market-data quality states backed by known evidence."""

    CURRENT = "CURRENT"
    STALE = "STALE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class DashboardPerformanceWarningCode(StrEnum):
    """Stable warnings emitted by dashboard performance orchestration."""

    BENCHMARK_NOT_FOUND = "BENCHMARK_NOT_FOUND"
    BENCHMARK_NO_DATA = "BENCHMARK_NO_DATA"
    BENCHMARK_PROVIDER_FAILED = "BENCHMARK_PROVIDER_FAILED"
    BENCHMARK_MISSING_OBSERVATION = "BENCHMARK_MISSING_OBSERVATION"


@dataclass(frozen=True, slots=True)
class DashboardPerformanceWarning:
    """One display-ready warning attached to the performance result."""

    code: str
    message: str
    observation_date: date | None = None
    asset_id: UUID | None = None
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class PortfolioPerformancePoint:
    """One aligned portfolio chart point without presentation interpolation."""

    observation_date: date
    portfolio_value: Decimal | None
    net_external_flow: Decimal
    daily_return: float | None
    cumulative_return: float | None
    data_quality: PerformanceDataQualityState
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkPerformancePoint:
    """One exact-date benchmark point aligned to the portfolio series."""

    observation_date: date
    adjusted_close: Decimal | None
    cumulative_return: float | None
    data_quality: PerformanceDataQualityState


@dataclass(frozen=True, slots=True)
class PortfolioPerformanceSummary:
    """Headline selected-period values with cash-flow semantics kept explicit."""

    starting_value: Decimal | None
    ending_value: Decimal | None
    value_change: Decimal | None
    net_external_flow: Decimal
    investment_gain_loss: Decimal | None
    cumulative_return: float | None
    benchmark_cumulative_return: float | None


@dataclass(frozen=True, slots=True)
class DashboardPerformanceProvenance:
    """Display-facing provenance and effective-range metadata."""

    portfolio_id: UUID
    base_currency: str
    provider: str
    requested_start: date
    requested_end_exclusive: date
    effective_start: date
    effective_end_exclusive: date
    data_as_of: datetime | None
    calculated_at: datetime
    engine_version: str
    price_field: str
    benchmark_asset_id: UUID | None
    benchmark_symbol: str | None


@dataclass(frozen=True, slots=True)
class DashboardPerformanceResult:
    """Complete display-ready performance payload for the dashboard hero."""

    summary: PortfolioPerformanceSummary
    points: tuple[PortfolioPerformancePoint, ...]
    benchmark_points: tuple[BenchmarkPerformancePoint, ...]
    portfolio_data_quality: PerformanceDataQualityState
    benchmark_data_quality: PerformanceDataQualityState | None
    warnings: tuple[DashboardPerformanceWarning, ...]
    provenance: DashboardPerformanceProvenance


def build_owned_portfolio_dashboard_performance(
    *,
    user: User,
    portfolio_id: UUID,
    valuation_times: tuple[datetime, ...],
    requested_start: date,
    requested_end: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    calculated_at: datetime,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardPerformanceResult:
    """Build a chart-ready portfolio/benchmark series with explicit gaps."""
    _validate_request_context(
        valuation_times=valuation_times,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
    )
    portfolio = (
        Portfolio.objects.owned_by(user).select_related("benchmark_asset").get(id=portfolio_id)
    )
    performance = calculate_owned_portfolio_daily_performance(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
    )
    points = _portfolio_points(performance)
    warnings = list(_portfolio_warnings(performance.warnings))

    benchmark_points: tuple[BenchmarkPerformancePoint, ...] = ()
    benchmark_quality: PerformanceDataQualityState | None = None
    benchmark_retrieved_at: datetime | None = None
    benchmark_symbol: str | None = None

    if portfolio.benchmark_asset is not None:
        benchmark_symbol = portfolio.benchmark_asset.symbol
        (
            benchmark_points,
            benchmark_quality,
            benchmark_retrieved_at,
            benchmark_warnings,
        ) = _benchmark_series(
            benchmark_asset_id=portfolio.benchmark_asset_id,
            benchmark_symbol=benchmark_symbol,
            observation_dates=tuple(point.observation_date for point in points),
            provider_name=performance.provenance.provider,
            resolver=resolver,
            provider=provider,
            executor=executor,
        )
        warnings.extend(benchmark_warnings)

    data_as_of = _latest_timestamp(
        performance.provenance.retrieved_at,
        benchmark_retrieved_at,
    )

    return DashboardPerformanceResult(
        summary=_summary(
            performance=performance,
            benchmark_points=benchmark_points,
        ),
        points=points,
        benchmark_points=benchmark_points,
        portfolio_data_quality=_overall_portfolio_quality(points),
        benchmark_data_quality=benchmark_quality,
        warnings=tuple(warnings),
        provenance=DashboardPerformanceProvenance(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            provider=performance.provenance.provider,
            requested_start=requested_start,
            requested_end_exclusive=requested_end,
            effective_start=points[0].observation_date,
            effective_end_exclusive=points[-1].observation_date + timedelta(days=1),
            data_as_of=data_as_of,
            calculated_at=calculated_at,
            engine_version=PORTFOLIO_ENGINE_VERSION,
            price_field="adjusted_close",
            benchmark_asset_id=portfolio.benchmark_asset_id,
            benchmark_symbol=benchmark_symbol,
        ),
    )


def _validate_request_context(
    *,
    valuation_times: tuple[datetime, ...],
    requested_start: date,
    requested_end: date,
    calculated_at: datetime,
) -> None:
    if requested_start >= requested_end:
        raise DashboardPerformanceError("requested_start must be before requested_end")

    if len(valuation_times) < 2:
        raise DashboardPerformanceError(
            "dashboard performance requires at least two valuation times"
        )

    if timezone.is_naive(calculated_at):
        raise DashboardPerformanceError("calculated_at must be timezone-aware")

    effective_dates = tuple(value.date() for value in valuation_times)
    if effective_dates[0] < requested_start or effective_dates[-1] >= requested_end:
        raise DashboardPerformanceError(
            "valuation times must remain inside the requested inclusive-start/exclusive-end range"
        )


def _portfolio_points(
    performance: DailyPortfolioPerformanceResult,
) -> tuple[PortfolioPerformancePoint, ...]:
    daily_returns: dict[date, float] = {}
    cumulative_returns: dict[date, float] = {}

    if performance.twr is not None:
        growth_factor = 1.0
        cumulative_returns[performance.twr.period_start] = 0.0

        for item in performance.twr.daily_returns:
            daily_returns[item.valuation_date] = item.simple_return
            growth_factor *= 1.0 + item.simple_return
            cumulative_returns[item.valuation_date] = growth_factor - 1.0

    return tuple(
        PortfolioPerformancePoint(
            observation_date=valuation.as_of.date(),
            portfolio_value=valuation.total_value,
            net_external_flow=valuation.net_external_flow,
            daily_return=daily_returns.get(valuation.as_of.date()),
            cumulative_return=cumulative_returns.get(valuation.as_of.date()),
            data_quality=_valuation_quality(valuation),
            warnings=tuple(warning.message for warning in valuation.warnings),
        )
        for valuation in performance.valuations
    )


def _valuation_quality(
    valuation: DailyPortfolioValuation,
) -> PerformanceDataQualityState:
    if not valuation.is_complete:
        if not valuation.positions:
            return PerformanceDataQualityState.UNAVAILABLE
        return PerformanceDataQualityState.PARTIAL

    if any(
        warning.code is DailyPerformanceWarningCode.STALE_PRICE_USED
        for warning in valuation.warnings
    ):
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT


def _overall_portfolio_quality(
    points: tuple[PortfolioPerformancePoint, ...],
) -> PerformanceDataQualityState:
    states = tuple(point.data_quality for point in points)

    if all(state is PerformanceDataQualityState.UNAVAILABLE for state in states):
        return PerformanceDataQualityState.UNAVAILABLE

    if any(
        state
        in (
            PerformanceDataQualityState.PARTIAL,
            PerformanceDataQualityState.UNAVAILABLE,
        )
        for state in states
    ):
        return PerformanceDataQualityState.PARTIAL

    if any(state is PerformanceDataQualityState.STALE for state in states):
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT


def _portfolio_warnings(
    warnings: tuple[DailyPerformanceWarning, ...],
) -> tuple[DashboardPerformanceWarning, ...]:
    return tuple(
        DashboardPerformanceWarning(
            code=warning.code.value,
            message=warning.message,
            observation_date=warning.valuation_at.date(),
            asset_id=warning.asset_id,
            symbol=warning.symbol,
        )
        for warning in warnings
    )


def _benchmark_series(
    *,
    benchmark_asset_id: UUID | None,
    benchmark_symbol: str,
    observation_dates: tuple[date, ...],
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> tuple[
    tuple[BenchmarkPerformancePoint, ...],
    PerformanceDataQualityState,
    datetime | None,
    tuple[DashboardPerformanceWarning, ...],
]:
    if benchmark_asset_id is None:
        raise DashboardPerformanceError(
            "benchmark_asset_id is required when benchmark_symbol is present"
        )

    query = normalize_market_bar_query(
        (benchmark_symbol,),
        start=observation_dates[0],
        end=observation_dates[-1] + timedelta(days=1),
        provider=provider_name,
    )
    batch = executor(
        query,
        resolver=resolver,
        provider=provider,
    )

    if batch.meta.provider != provider_name:
        raise DashboardPerformanceError(
            "portfolio and benchmark series returned inconsistent providers"
        )

    symbol_result = next(
        (result for result in batch.results if result.symbol == benchmark_symbol),
        None,
    )

    if symbol_result is None:
        return _unavailable_benchmark(
            observation_dates=observation_dates,
            code=DashboardPerformanceWarningCode.BENCHMARK_NOT_FOUND,
            message=("Configured benchmark did not return a market-data result."),
            benchmark_asset_id=benchmark_asset_id,
            benchmark_symbol=benchmark_symbol,
            retrieved_at=batch.meta.retrieved_at,
        )

    if symbol_result.status is not MarketBarStatus.SUCCEEDED:
        return _benchmark_issue_result(
            observation_dates=observation_dates,
            symbol_result=symbol_result,
            benchmark_asset_id=benchmark_asset_id,
            benchmark_symbol=benchmark_symbol,
            retrieved_at=batch.meta.retrieved_at,
        )

    return _successful_benchmark_series(
        observation_dates=observation_dates,
        symbol_result=symbol_result,
        benchmark_asset_id=benchmark_asset_id,
        benchmark_symbol=benchmark_symbol,
        retrieved_at=batch.meta.retrieved_at,
    )


def _successful_benchmark_series(
    *,
    observation_dates: tuple[date, ...],
    symbol_result: MarketBarSymbolResult,
    benchmark_asset_id: UUID,
    benchmark_symbol: str,
    retrieved_at: datetime,
) -> tuple[
    tuple[BenchmarkPerformancePoint, ...],
    PerformanceDataQualityState,
    datetime,
    tuple[DashboardPerformanceWarning, ...],
]:
    prices_by_date = {
        bar.trade_date: Decimal(str(bar.adjusted_close))
        for bar in symbol_result.bars
        if bar.adjusted_close is not None
    }
    base_price = prices_by_date.get(observation_dates[0])
    points: list[BenchmarkPerformancePoint] = []
    warnings: list[DashboardPerformanceWarning] = []

    for observation_date in observation_dates:
        price = prices_by_date.get(observation_date)

        if price is None:
            points.append(
                BenchmarkPerformancePoint(
                    observation_date=observation_date,
                    adjusted_close=None,
                    cumulative_return=None,
                    data_quality=PerformanceDataQualityState.PARTIAL,
                )
            )
            warnings.append(
                DashboardPerformanceWarning(
                    code=(DashboardPerformanceWarningCode.BENCHMARK_MISSING_OBSERVATION.value),
                    message=(
                        "Benchmark has no adjusted-close observation for the "
                        "aligned portfolio date; no value was interpolated."
                    ),
                    observation_date=observation_date,
                    asset_id=benchmark_asset_id,
                    symbol=benchmark_symbol,
                )
            )
            continue

        cumulative_return = None
        if base_price is not None:
            cumulative_return = float(price / base_price - Decimal("1"))

        points.append(
            BenchmarkPerformancePoint(
                observation_date=observation_date,
                adjusted_close=price,
                cumulative_return=cumulative_return,
                data_quality=PerformanceDataQualityState.CURRENT,
            )
        )

    quality = (
        PerformanceDataQualityState.CURRENT
        if all(point.adjusted_close is not None for point in points)
        else PerformanceDataQualityState.PARTIAL
    )

    if base_price is None:
        quality = PerformanceDataQualityState.PARTIAL

    return tuple(points), quality, retrieved_at, tuple(warnings)


def _benchmark_issue_result(
    *,
    observation_dates: tuple[date, ...],
    symbol_result: MarketBarSymbolResult,
    benchmark_asset_id: UUID,
    benchmark_symbol: str,
    retrieved_at: datetime,
) -> tuple[
    tuple[BenchmarkPerformancePoint, ...],
    PerformanceDataQualityState,
    datetime,
    tuple[DashboardPerformanceWarning, ...],
]:
    if symbol_result.status is MarketBarStatus.NOT_FOUND:
        code = DashboardPerformanceWarningCode.BENCHMARK_NOT_FOUND
        message = "Configured benchmark could not be resolved."
    elif symbol_result.status is MarketBarStatus.NO_DATA:
        code = DashboardPerformanceWarningCode.BENCHMARK_NO_DATA
        message = "Configured benchmark has no data for the requested period."
    else:
        code = DashboardPerformanceWarningCode.BENCHMARK_PROVIDER_FAILED
        message = "Provider failed to return usable benchmark data."

    return _unavailable_benchmark(
        observation_dates=observation_dates,
        code=code,
        message=message,
        benchmark_asset_id=benchmark_asset_id,
        benchmark_symbol=benchmark_symbol,
        retrieved_at=retrieved_at,
    )


def _unavailable_benchmark(
    *,
    observation_dates: tuple[date, ...],
    code: DashboardPerformanceWarningCode,
    message: str,
    benchmark_asset_id: UUID,
    benchmark_symbol: str,
    retrieved_at: datetime,
) -> tuple[
    tuple[BenchmarkPerformancePoint, ...],
    PerformanceDataQualityState,
    datetime,
    tuple[DashboardPerformanceWarning, ...],
]:
    points = tuple(
        BenchmarkPerformancePoint(
            observation_date=observation_date,
            adjusted_close=None,
            cumulative_return=None,
            data_quality=PerformanceDataQualityState.UNAVAILABLE,
        )
        for observation_date in observation_dates
    )
    warning = DashboardPerformanceWarning(
        code=code.value,
        message=message,
        asset_id=benchmark_asset_id,
        symbol=benchmark_symbol,
    )
    return (
        points,
        PerformanceDataQualityState.UNAVAILABLE,
        retrieved_at,
        (warning,),
    )


def _summary(
    *,
    performance: DailyPortfolioPerformanceResult,
    benchmark_points: tuple[BenchmarkPerformancePoint, ...],
) -> PortfolioPerformanceSummary:
    first_value = performance.valuations[0].total_value
    last_value = performance.valuations[-1].total_value
    net_external_flow = sum(
        (valuation.net_external_flow for valuation in performance.valuations),
        ZERO,
    )

    value_change: Decimal | None = None
    investment_gain_loss: Decimal | None = None

    if first_value is not None and last_value is not None:
        value_change = last_value - first_value
        investment_gain_loss = value_change - net_external_flow

    benchmark_return = None
    if benchmark_points:
        benchmark_return = benchmark_points[-1].cumulative_return

    return PortfolioPerformanceSummary(
        starting_value=first_value,
        ending_value=last_value,
        value_change=value_change,
        net_external_flow=net_external_flow,
        investment_gain_loss=investment_gain_loss,
        cumulative_return=(
            performance.twr.cumulative_return if performance.twr is not None else None
        ),
        benchmark_cumulative_return=benchmark_return,
    )


def _latest_timestamp(
    first: datetime | None,
    second: datetime | None,
) -> datetime | None:
    if first is None:
        return second

    if second is None:
        return first

    return max(first, second)
