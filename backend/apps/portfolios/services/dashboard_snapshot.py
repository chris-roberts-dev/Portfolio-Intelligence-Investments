"""Canonical owner-scoped dashboard snapshot composition.

This service gives the dashboard one immutable calculation context while
preserving the existing module contracts. A request-local market-bar executor
memoizes identical normalized queries so composing multiple cards does not
multiply provider calls.

Shared current valuation and daily performance are computed once for
review-item aggregation and top-level provenance, while the single analytics
module result is reused by review-item aggregation. Existing dashboard modules
retain their proven orchestration; repeated identical market-data queries are
served from the request-local memoizer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from django.utils import timezone

from apps.accounts.models import User
from apps.market_data.contracts import (
    MarketBarBatchResult,
    MarketBarQueryError,
    NormalizedMarketBarQuery,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.providers.safety import sanitize_provider_message
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
from apps.portfolios.services.analytics import (
    PortfolioAnalyticsError,
    PortfolioAnalyticsResult,
    analyze_owned_portfolio,
)
from apps.portfolios.services.book_accounting import BookAccountingError
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentValuationError,
    MarketBarQueryExecutor,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceError,
    DailyPortfolioPerformanceResult,
    calculate_owned_portfolio_daily_performance,
)
from apps.portfolios.services.dashboard_allocation import (
    DashboardAllocationError,
    DashboardAllocationResult,
    build_owned_portfolio_dashboard_allocation,
)
from apps.portfolios.services.dashboard_holdings import (
    DashboardHoldingsError,
    DashboardHoldingsResult,
    build_owned_portfolio_dashboard_holdings,
)
from apps.portfolios.services.dashboard_movers import (
    DashboardMoversError,
    DashboardMoversResult,
    build_owned_portfolio_dashboard_movers,
)
from apps.portfolios.services.dashboard_performance import (
    DashboardPerformanceError,
    DashboardPerformanceResult,
    build_owned_portfolio_dashboard_performance,
)
from apps.portfolios.services.dashboard_review_items import (
    DashboardReviewItemsError,
    DashboardReviewItemsResult,
    aggregate_dashboard_review_items,
)
from apps.portfolios.services.dashboard_summary import (
    DashboardPortfolioSummaryError,
    DashboardPortfolioSummaryResult,
    build_owned_portfolio_dashboard_summary,
)
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


class DashboardSnapshotError(ValueError):
    """Raised when the shared dashboard request context is invalid."""


class DashboardSnapshotModule(StrEnum):
    """Stable modules composed into one dashboard snapshot."""

    SUMMARY = "SUMMARY"
    PERFORMANCE = "PERFORMANCE"
    ALLOCATION = "ALLOCATION"
    HOLDINGS = "HOLDINGS"
    MOVERS = "MOVERS"
    ANALYTICS = "ANALYTICS"
    REVIEW_ITEMS = "REVIEW_ITEMS"


class DashboardSnapshotModuleStatus(StrEnum):
    """Whether one module was composed successfully for the snapshot."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class DashboardSnapshotModuleState:
    """Local availability/error state for one dashboard module."""

    module: DashboardSnapshotModule
    status: DashboardSnapshotModuleStatus
    error_code: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class DashboardSnapshotContext:
    """Immutable identity and cutoff shared by every dashboard module."""

    snapshot_id: UUID
    portfolio_id: UUID
    base_currency: str
    provider: str
    requested_start: date
    requested_end_exclusive: date
    effective_start: date
    effective_end_exclusive: date
    valuation_cutoff: datetime
    calculated_at: datetime
    engine_version: str
    current_data_as_of: datetime | None
    historical_data_as_of: datetime | None
    analytics_as_of_date: date | None


@dataclass(frozen=True, slots=True)
class DashboardSnapshotResult:
    """One coherent dashboard payload with independently degradable modules."""

    snapshot: DashboardSnapshotContext
    is_complete: bool
    modules: tuple[DashboardSnapshotModuleState, ...]
    summary: DashboardPortfolioSummaryResult | None
    performance: DashboardPerformanceResult | None
    allocation: DashboardAllocationResult | None
    holdings: DashboardHoldingsResult | None
    movers: DashboardMoversResult | None
    analytics: PortfolioAnalyticsResult | None
    review_items: DashboardReviewItemsResult | None


class MemoizedMarketBarQueryExecutor:
    """Request-local memoizer for identical provider-neutral market-bar queries."""

    def __init__(
        self,
        delegate: MarketBarQueryExecutor = execute_market_bar_query,
    ) -> None:
        self._delegate = delegate
        self._cache: dict[NormalizedMarketBarQuery, MarketBarBatchResult] = {}
        self.executed_queries = 0
        self.reused_queries = 0

    def __call__(
        self,
        query: NormalizedMarketBarQuery,
        *,
        resolver: AssetResolver,
        provider: MarketDataProvider,
    ) -> MarketBarBatchResult:
        """Return one cached result or execute the normalized query once."""
        cached = self._cache.get(query)

        if cached is not None:
            self.reused_queries += 1
            return cached

        result = self._delegate(
            query,
            resolver=resolver,
            provider=provider,
        )
        self._cache[query] = result
        self.executed_queries += 1
        return result


def build_owned_portfolio_dashboard_snapshot(
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
    movers_limit: int,
    risk_free_rate_annual: float,
    minimum_acceptable_return_annual: float,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardSnapshotResult:
    """Compose one dashboard snapshot against a common immutable cutoff."""
    _validate_snapshot_context(
        valuation_times=valuation_times,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
        movers_limit=movers_limit,
    )
    portfolio = (
        Portfolio.objects.owned_by(user).select_related("benchmark_asset").get(id=portfolio_id)
    )
    memoized_executor = MemoizedMarketBarQueryExecutor(executor)
    observation_dates = tuple(value.date() for value in valuation_times)

    current = _shared_current_valuation(
        user=user,
        portfolio_id=portfolio_id,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        calculated_at=calculated_at,
        executor=memoized_executor,
    )
    daily_performance = _shared_daily_performance(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=memoized_executor,
    )

    summary, summary_state = _run_module(
        DashboardSnapshotModule.SUMMARY,
        lambda: build_owned_portfolio_dashboard_summary(
            user=user,
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
            executor=memoized_executor,
        ),
    )
    performance, performance_state = _run_module(
        DashboardSnapshotModule.PERFORMANCE,
        lambda: build_owned_portfolio_dashboard_performance(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            requested_start=requested_start,
            requested_end=requested_end,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
            executor=memoized_executor,
        ),
    )
    allocation, allocation_state = _run_module(
        DashboardSnapshotModule.ALLOCATION,
        lambda: build_owned_portfolio_dashboard_allocation(
            user=user,
            portfolio_id=portfolio_id,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
            executor=memoized_executor,
        ),
    )
    holdings, holdings_state = _run_module(
        DashboardSnapshotModule.HOLDINGS,
        lambda: build_owned_portfolio_dashboard_holdings(
            user=user,
            portfolio_id=portfolio_id,
            observation_dates=observation_dates,
            requested_start=requested_start,
            requested_end=requested_end,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
            executor=memoized_executor,
        ),
    )
    movers, movers_state = _run_module(
        DashboardSnapshotModule.MOVERS,
        lambda: build_owned_portfolio_dashboard_movers(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            requested_start=requested_start,
            requested_end=requested_end,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            calculated_at=calculated_at,
            limit=movers_limit,
            executor=memoized_executor,
        ),
    )
    analytics, analytics_state = _run_module(
        DashboardSnapshotModule.ANALYTICS,
        lambda: analyze_owned_portfolio(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            risk_free_rate_annual=risk_free_rate_annual,
            minimum_acceptable_return_annual=minimum_acceptable_return_annual,
            executor=memoized_executor,
        ),
    )
    review_items, review_items_state = _review_items_module(
        portfolio=portfolio,
        valuation_times=valuation_times,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
        current=current,
        performance=daily_performance,
        analytics=analytics,
    )

    modules = (
        summary_state,
        performance_state,
        allocation_state,
        holdings_state,
        movers_state,
        analytics_state,
        review_items_state,
    )
    context = DashboardSnapshotContext(
        snapshot_id=_snapshot_id(
            portfolio_id=portfolio.id,
            provider=provider_name,
            requested_start=requested_start,
            requested_end=requested_end,
            effective_start=observation_dates[0],
            effective_end=observation_dates[-1] + timedelta(days=1),
            calculated_at=calculated_at,
        ),
        portfolio_id=portfolio.id,
        base_currency=portfolio.base_currency,
        provider=provider_name,
        requested_start=requested_start,
        requested_end_exclusive=requested_end,
        effective_start=observation_dates[0],
        effective_end_exclusive=observation_dates[-1] + timedelta(days=1),
        valuation_cutoff=calculated_at,
        calculated_at=calculated_at,
        engine_version=PORTFOLIO_ENGINE_VERSION,
        current_data_as_of=_current_data_as_of(
            current=current,
            summary=summary,
            allocation=allocation,
        ),
        historical_data_as_of=_historical_data_as_of(
            performance=daily_performance,
            dashboard_performance=performance,
        ),
        analytics_as_of_date=(analytics.provenance.as_of_date if analytics is not None else None),
    )

    return DashboardSnapshotResult(
        snapshot=context,
        is_complete=all(
            state.status is DashboardSnapshotModuleStatus.AVAILABLE for state in modules
        ),
        modules=modules,
        summary=summary,
        performance=performance,
        allocation=allocation,
        holdings=holdings,
        movers=movers,
        analytics=analytics,
        review_items=review_items,
    )


def _shared_current_valuation(
    *,
    user: User,
    portfolio_id: UUID,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    calculated_at: datetime,
    executor: MarketBarQueryExecutor,
) -> CurrentPortfolioValuationResult | None:
    try:
        return value_owned_portfolio(
            user=user,
            portfolio_id=portfolio_id,
            as_of=calculated_at,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            executor=executor,
        )
    except (CurrentValuationError, MarketBarQueryError):
        return None


def _shared_daily_performance(
    *,
    user: User,
    portfolio_id: UUID,
    valuation_times: tuple[datetime, ...],
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    executor: MarketBarQueryExecutor,
) -> DailyPortfolioPerformanceResult | None:
    try:
        return calculate_owned_portfolio_daily_performance(
            user=user,
            portfolio_id=portfolio_id,
            valuation_times=valuation_times,
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            trading_calendar=trading_calendar,
            executor=executor,
        )
    except (DailyPerformanceError, CurrentValuationError, MarketBarQueryError):
        return None


def _run_module[T](
    module: DashboardSnapshotModule,
    callback: Callable[[], T],
) -> tuple[T | None, DashboardSnapshotModuleState]:
    try:
        result = callback()
    except (
        BookAccountingError,
        CurrentValuationError,
        DailyPerformanceError,
        DashboardAllocationError,
        DashboardHoldingsError,
        DashboardMoversError,
        DashboardPerformanceError,
        DashboardPortfolioSummaryError,
        DashboardReviewItemsError,
        MarketBarQueryError,
        PortfolioAnalyticsError,
    ) as exc:
        return (
            None,
            DashboardSnapshotModuleState(
                module=module,
                status=DashboardSnapshotModuleStatus.UNAVAILABLE,
                error_code=f"{module.value}_UNAVAILABLE",
                detail=sanitize_provider_message(str(exc)),
            ),
        )

    return (
        result,
        DashboardSnapshotModuleState(
            module=module,
            status=DashboardSnapshotModuleStatus.AVAILABLE,
        ),
    )


def _review_items_module(
    *,
    portfolio: Portfolio,
    valuation_times: tuple[datetime, ...],
    requested_start: date,
    requested_end: date,
    calculated_at: datetime,
    current: CurrentPortfolioValuationResult | None,
    performance: DailyPortfolioPerformanceResult | None,
    analytics: PortfolioAnalyticsResult | None,
) -> tuple[
    DashboardReviewItemsResult | None,
    DashboardSnapshotModuleState,
]:
    if current is None or performance is None or analytics is None:
        return (
            None,
            DashboardSnapshotModuleState(
                module=DashboardSnapshotModule.REVIEW_ITEMS,
                status=DashboardSnapshotModuleStatus.UNAVAILABLE,
                error_code="REVIEW_ITEMS_SOURCE_UNAVAILABLE",
                detail=(
                    "Review items require current valuation, daily performance, "
                    "and analytics from the shared snapshot context."
                ),
            ),
        )

    return _run_module(
        DashboardSnapshotModule.REVIEW_ITEMS,
        lambda: aggregate_dashboard_review_items(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            requested_start=requested_start,
            requested_end=requested_end,
            valuation_times=valuation_times,
            current=current,
            performance=performance,
            analytics=analytics,
            calculated_at=calculated_at,
        ),
    )


def _validate_snapshot_context(
    *,
    valuation_times: tuple[datetime, ...],
    requested_start: date,
    requested_end: date,
    calculated_at: datetime,
    movers_limit: int,
) -> None:
    if requested_start >= requested_end:
        raise DashboardSnapshotError("requested_start must be before requested_end")

    if len(valuation_times) < 2:
        raise DashboardSnapshotError("dashboard snapshot requires at least two valuation times")

    if tuple(sorted(set(valuation_times))) != valuation_times:
        raise DashboardSnapshotError("valuation_times must be unique and strictly ascending")

    if any(timezone.is_naive(value) for value in valuation_times):
        raise DashboardSnapshotError("valuation_times must be timezone-aware")

    if timezone.is_naive(calculated_at):
        raise DashboardSnapshotError("calculated_at must be timezone-aware")

    if valuation_times[-1] > calculated_at:
        raise DashboardSnapshotError("valuation_times must not extend beyond the snapshot cutoff")

    if valuation_times[0].date() < requested_start or valuation_times[-1].date() >= requested_end:
        raise DashboardSnapshotError("valuation times must remain inside the requested range")

    if not 1 <= movers_limit <= 20:
        raise DashboardSnapshotError("movers_limit must be between 1 and 20")


def _current_data_as_of(
    *,
    current: CurrentPortfolioValuationResult | None,
    summary: DashboardPortfolioSummaryResult | None,
    allocation: DashboardAllocationResult | None,
) -> datetime | None:
    if current is not None:
        return current.provenance.retrieved_at

    if summary is not None:
        return summary.provenance.current_price_data_as_of

    if allocation is not None:
        return allocation.provenance.data_as_of

    return None


def _historical_data_as_of(
    *,
    performance: DailyPortfolioPerformanceResult | None,
    dashboard_performance: DashboardPerformanceResult | None,
) -> datetime | None:
    if performance is not None:
        return performance.provenance.retrieved_at

    if dashboard_performance is not None:
        return dashboard_performance.provenance.data_as_of

    return None


def _snapshot_id(
    *,
    portfolio_id: UUID,
    provider: str,
    requested_start: date,
    requested_end: date,
    effective_start: date,
    effective_end: date,
    calculated_at: datetime,
) -> UUID:
    payload = "|".join(
        (
            str(portfolio_id),
            provider,
            requested_start.isoformat(),
            requested_end.isoformat(),
            effective_start.isoformat(),
            effective_end.isoformat(),
            calculated_at.isoformat(),
            PORTFOLIO_ENGINE_VERSION,
        )
    )
    return uuid5(
        NAMESPACE_URL,
        f"portfolio-intelligence/dashboard-snapshot/{payload}",
    )
