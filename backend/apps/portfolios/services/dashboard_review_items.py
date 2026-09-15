"""Stable dashboard data-quality alerts and review items.

Only conditions already proven by current valuation, historical performance,
and analytical application contracts are promoted into review items. This
module deliberately does not invent policies for account synchronization,
classification, corporate actions, allocation drift, or concentration
thresholds.

Analytics SOURCE_WARNING entries are omitted because the underlying daily
performance warnings are aggregated directly with their richer asset/date
context. BENCHMARK_NOT_CONFIGURED is also omitted because benchmark comparison
is optional in the dashboard contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
from apps.portfolios.services.analytics import (
    PortfolioAnalyticsResult,
    PortfolioAnalyticsWarning,
    PortfolioAnalyticsWarningCode,
    analyze_owned_portfolio,
)
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentValuationWarning,
    CurrentValuationWarningCode,
    MarketBarQueryExecutor,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceWarning,
    DailyPerformanceWarningCode,
    DailyPortfolioPerformanceResult,
    calculate_owned_portfolio_daily_performance,
)


class DashboardReviewItemsError(ValueError):
    """Raised when review-item aggregation cannot satisfy its contract."""


class ReviewItemSeverity(StrEnum):
    """Stable attention levels for dashboard review items."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ReviewItemCategory(StrEnum):
    """Stable categories backed by currently implemented source contracts."""

    MARKET_DATA = "MARKET_DATA"
    DATA_COVERAGE = "DATA_COVERAGE"
    PROVIDER = "PROVIDER"
    VALUATION = "VALUATION"
    ANALYTICS = "ANALYTICS"


class ReviewItemSource(StrEnum):
    """Authoritative application source that emitted the condition."""

    CURRENT_VALUATION = "CURRENT_VALUATION"
    DAILY_PERFORMANCE = "DAILY_PERFORMANCE"
    ANALYTICS = "ANALYTICS"


class ReviewDrilldownResource(StrEnum):
    """Existing owner-scoped dashboard resource supporting investigation."""

    HOLDINGS = "HOLDINGS"
    PERFORMANCE = "PERFORMANCE"
    ANALYTICS = "ANALYTICS"


@dataclass(frozen=True, slots=True)
class DashboardReviewDrilldown:
    """Semantic owner-scoped reference for investigating one review item."""

    resource: ReviewDrilldownResource
    portfolio_id: UUID
    requested_start: date
    requested_end_exclusive: date
    asset_id: UUID | None = None
    symbol: str | None = None
    observation_date: date | None = None


@dataclass(frozen=True, slots=True)
class DashboardReviewItem:
    """One stable dashboard alert or review item."""

    key: str
    source: ReviewItemSource
    severity: ReviewItemSeverity
    category: ReviewItemCategory
    code: str
    message: str
    drilldown: DashboardReviewDrilldown


@dataclass(frozen=True, slots=True)
class DashboardReviewCount:
    """One deterministic count bucket."""

    key: str
    count: int


@dataclass(frozen=True, slots=True)
class DashboardReviewCounts:
    """Unfiltered alert counts used by intelligence-panel badges."""

    total: int
    by_severity: tuple[DashboardReviewCount, ...]
    by_category: tuple[DashboardReviewCount, ...]


@dataclass(frozen=True, slots=True)
class DashboardReviewFilters:
    """Filters applied only to the returned detail-item collection."""

    severity: ReviewItemSeverity | None
    category: ReviewItemCategory | None


@dataclass(frozen=True, slots=True)
class DashboardReviewProvenance:
    """Calculation and data provenance for review-item aggregation."""

    portfolio_id: UUID
    base_currency: str
    provider: str
    requested_start: date
    requested_end_exclusive: date
    effective_start: date
    effective_end_exclusive: date
    current_data_as_of: datetime | None
    historical_data_as_of: datetime | None
    analytics_as_of_date: date
    calculated_at: datetime
    engine_version: str
    included_sources: tuple[ReviewItemSource, ...]
    ordering_rule: str


@dataclass(frozen=True, slots=True)
class DashboardReviewItemsResult:
    """Complete dashboard review-item response."""

    counts: DashboardReviewCounts
    filtered_count: int
    filters: DashboardReviewFilters
    items: tuple[DashboardReviewItem, ...]
    provenance: DashboardReviewProvenance


_SEVERITY_ORDER = {
    ReviewItemSeverity.ERROR: 0,
    ReviewItemSeverity.WARNING: 1,
    ReviewItemSeverity.INFO: 2,
}

_IGNORED_ANALYTICS_CODES = frozenset(
    {
        PortfolioAnalyticsWarningCode.SOURCE_WARNING,
        PortfolioAnalyticsWarningCode.BENCHMARK_NOT_CONFIGURED,
    }
)


def build_owned_portfolio_dashboard_review_items(
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
    severity: ReviewItemSeverity | None = None,
    category: ReviewItemCategory | None = None,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardReviewItemsResult:
    """Build owner-scoped review items from existing warning contracts."""
    _validate_request_context(
        valuation_times=valuation_times,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
    )
    portfolio = Portfolio.objects.owned_by(user).get(id=portfolio_id)

    current = value_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        as_of=calculated_at,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
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
    analytics = analyze_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
    )

    return aggregate_dashboard_review_items(
        portfolio_id=portfolio.id,
        base_currency=portfolio.base_currency,
        requested_start=requested_start,
        requested_end=requested_end,
        valuation_times=valuation_times,
        current=current,
        performance=performance,
        analytics=analytics,
        calculated_at=calculated_at,
        severity=severity,
        category=category,
    )


def aggregate_dashboard_review_items(
    *,
    portfolio_id: UUID,
    base_currency: str,
    requested_start: date,
    requested_end: date,
    valuation_times: tuple[datetime, ...],
    current: CurrentPortfolioValuationResult,
    performance: DailyPortfolioPerformanceResult,
    analytics: PortfolioAnalyticsResult,
    calculated_at: datetime,
    severity: ReviewItemSeverity | None = None,
    category: ReviewItemCategory | None = None,
) -> DashboardReviewItemsResult:
    """Aggregate already-computed results without performing provider calls."""
    _validate_request_context(
        valuation_times=valuation_times,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
    )
    provider_name = _consistent_provider(
        current=current,
        performance=performance,
        analytics=analytics,
    )

    items = [
        *_current_review_items(
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            current=current,
        ),
        *_performance_review_items(
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            performance=performance,
        ),
        *_analytics_review_items(
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            analytics=analytics,
        ),
    ]
    ordered_items = _deduplicate_and_order(tuple(items))
    counts = _review_counts(ordered_items)
    filtered_items = tuple(
        item
        for item in ordered_items
        if (severity is None or item.severity is severity)
        and (category is None or item.category is category)
    )

    return DashboardReviewItemsResult(
        counts=counts,
        filtered_count=len(filtered_items),
        filters=DashboardReviewFilters(
            severity=severity,
            category=category,
        ),
        items=filtered_items,
        provenance=DashboardReviewProvenance(
            portfolio_id=portfolio_id,
            base_currency=base_currency,
            provider=provider_name,
            requested_start=requested_start,
            requested_end_exclusive=requested_end,
            effective_start=valuation_times[0].date(),
            effective_end_exclusive=(valuation_times[-1].date() + timedelta(days=1)),
            current_data_as_of=current.provenance.retrieved_at,
            historical_data_as_of=performance.provenance.retrieved_at,
            analytics_as_of_date=analytics.provenance.as_of_date,
            calculated_at=calculated_at,
            engine_version=analytics.provenance.engine_version,
            included_sources=(
                ReviewItemSource.CURRENT_VALUATION,
                ReviewItemSource.DAILY_PERFORMANCE,
                ReviewItemSource.ANALYTICS,
            ),
            ordering_rule=("SEVERITY_THEN_CATEGORY_THEN_CODE_THEN_SYMBOL_DATE_V1"),
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
        raise DashboardReviewItemsError("requested_start must be before requested_end")

    if len(valuation_times) < 2:
        raise DashboardReviewItemsError(
            "dashboard review items require at least two valuation times"
        )

    if tuple(sorted(set(valuation_times))) != valuation_times:
        raise DashboardReviewItemsError("valuation_times must be unique and strictly ascending")

    if any(timezone.is_naive(value) for value in valuation_times):
        raise DashboardReviewItemsError("valuation_times must be timezone-aware")

    if valuation_times[0].date() < requested_start or valuation_times[-1].date() >= requested_end:
        raise DashboardReviewItemsError("valuation times must remain inside the requested range")

    if timezone.is_naive(calculated_at):
        raise DashboardReviewItemsError("calculated_at must be timezone-aware")


def _consistent_provider(
    *,
    current: CurrentPortfolioValuationResult,
    performance: DailyPortfolioPerformanceResult,
    analytics: PortfolioAnalyticsResult,
) -> str:
    providers = {
        current.provenance.provider,
        performance.provenance.provider,
        analytics.provenance.data_source,
    }

    if len(providers) != 1:
        raise DashboardReviewItemsError(
            "Review-item sources returned inconsistent provider provenance."
        )

    return providers.pop()


def _current_review_items(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    current: CurrentPortfolioValuationResult,
) -> tuple[DashboardReviewItem, ...]:
    items = [
        _current_warning_item(
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            warning=warning,
            observation_date=current.provenance.as_of.date(),
        )
        for warning in current.warnings
    ]

    if not current.is_complete:
        items.append(
            _make_item(
                portfolio_id=portfolio_id,
                requested_start=requested_start,
                requested_end=requested_end,
                source=ReviewItemSource.CURRENT_VALUATION,
                severity=ReviewItemSeverity.ERROR,
                category=ReviewItemCategory.VALUATION,
                code="CURRENT_VALUATION_INCOMPLETE",
                message=(
                    "Current portfolio valuation is incomplete because one "
                    "or more held assets lack an acceptable current price."
                ),
                resource=ReviewDrilldownResource.HOLDINGS,
                observation_date=current.provenance.as_of.date(),
            )
        )

    return tuple(items)


def _current_warning_item(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    warning: CurrentValuationWarning,
    observation_date: date,
) -> DashboardReviewItem:
    if warning.code is CurrentValuationWarningCode.STALE_PRICE_USED:
        severity = ReviewItemSeverity.WARNING
        category = ReviewItemCategory.MARKET_DATA
    elif warning.code is CurrentValuationWarningCode.PRICE_PROVIDER_FAILED:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.PROVIDER
    else:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.MARKET_DATA

    return _make_item(
        portfolio_id=portfolio_id,
        requested_start=requested_start,
        requested_end=requested_end,
        source=ReviewItemSource.CURRENT_VALUATION,
        severity=severity,
        category=category,
        code=warning.code.value,
        message=warning.message,
        resource=ReviewDrilldownResource.HOLDINGS,
        asset_id=warning.asset_id,
        symbol=warning.symbol,
        observation_date=observation_date,
    )


def _performance_review_items(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    performance: DailyPortfolioPerformanceResult,
) -> tuple[DashboardReviewItem, ...]:
    return tuple(
        _performance_warning_item(
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            warning=warning,
        )
        for warning in performance.warnings
    )


def _performance_warning_item(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    warning: DailyPerformanceWarning,
) -> DashboardReviewItem:
    if warning.code is DailyPerformanceWarningCode.STALE_PRICE_USED:
        severity = ReviewItemSeverity.WARNING
        category = ReviewItemCategory.MARKET_DATA
    elif warning.code is DailyPerformanceWarningCode.PRICE_PROVIDER_FAILED:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.PROVIDER
    elif warning.code is DailyPerformanceWarningCode.INCOMPLETE_VALUATION:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.VALUATION
    elif warning.code is DailyPerformanceWarningCode.TWR_UNDEFINED:
        severity = ReviewItemSeverity.WARNING
        category = ReviewItemCategory.ANALYTICS
    else:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.DATA_COVERAGE

    return _make_item(
        portfolio_id=portfolio_id,
        requested_start=requested_start,
        requested_end=requested_end,
        source=ReviewItemSource.DAILY_PERFORMANCE,
        severity=severity,
        category=category,
        code=warning.code.value,
        message=warning.message,
        resource=ReviewDrilldownResource.PERFORMANCE,
        asset_id=warning.asset_id,
        symbol=warning.symbol,
        observation_date=warning.valuation_at.date(),
    )


def _analytics_review_items(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    analytics: PortfolioAnalyticsResult,
) -> tuple[DashboardReviewItem, ...]:
    items: list[DashboardReviewItem] = []

    for warning in analytics.warnings:
        item = _analytics_warning_item(
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end=requested_end,
            analytics=analytics,
            warning=warning,
        )
        if item is not None:
            items.append(item)

    return tuple(items)


def _analytics_warning_item(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    analytics: PortfolioAnalyticsResult,
    warning: PortfolioAnalyticsWarning,
) -> DashboardReviewItem | None:
    if warning.code in _IGNORED_ANALYTICS_CODES:
        return None

    if warning.code is PortfolioAnalyticsWarningCode.BENCHMARK_PROVIDER_FAILED:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.PROVIDER
    elif warning.code in (
        PortfolioAnalyticsWarningCode.BENCHMARK_NOT_FOUND,
        PortfolioAnalyticsWarningCode.BENCHMARK_NO_DATA,
    ):
        severity = ReviewItemSeverity.WARNING
        category = ReviewItemCategory.DATA_COVERAGE
    elif warning.code is PortfolioAnalyticsWarningCode.PERFORMANCE_UNAVAILABLE:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.ANALYTICS
    elif warning.code is PortfolioAnalyticsWarningCode.CURRENT_VALUATION_INCOMPLETE:
        severity = ReviewItemSeverity.ERROR
        category = ReviewItemCategory.VALUATION
    else:
        severity = ReviewItemSeverity.WARNING
        category = ReviewItemCategory.ANALYTICS

    return _make_item(
        portfolio_id=portfolio_id,
        requested_start=requested_start,
        requested_end=requested_end,
        source=ReviewItemSource.ANALYTICS,
        severity=severity,
        category=category,
        code=warning.code.value,
        message=warning.message,
        resource=ReviewDrilldownResource.ANALYTICS,
        observation_date=analytics.provenance.as_of_date,
    )


def _make_item(
    *,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    source: ReviewItemSource,
    severity: ReviewItemSeverity,
    category: ReviewItemCategory,
    code: str,
    message: str,
    resource: ReviewDrilldownResource,
    asset_id: UUID | None = None,
    symbol: str | None = None,
    observation_date: date | None = None,
) -> DashboardReviewItem:
    key = ":".join(
        (
            source.value,
            code,
            str(asset_id) if asset_id is not None else "PORTFOLIO",
            observation_date.isoformat() if observation_date is not None else "-",
        )
    )

    return DashboardReviewItem(
        key=key,
        source=source,
        severity=severity,
        category=category,
        code=code,
        message=message,
        drilldown=DashboardReviewDrilldown(
            resource=resource,
            portfolio_id=portfolio_id,
            requested_start=requested_start,
            requested_end_exclusive=requested_end,
            asset_id=asset_id,
            symbol=symbol,
            observation_date=observation_date,
        ),
    )


def _deduplicate_and_order(
    items: tuple[DashboardReviewItem, ...],
) -> tuple[DashboardReviewItem, ...]:
    by_key: dict[str, DashboardReviewItem] = {}

    for item in items:
        by_key.setdefault(item.key, item)

    return tuple(
        sorted(
            by_key.values(),
            key=lambda item: (
                _SEVERITY_ORDER[item.severity],
                item.category.value,
                item.code,
                item.drilldown.symbol or "",
                (
                    item.drilldown.observation_date.isoformat()
                    if item.drilldown.observation_date is not None
                    else ""
                ),
                item.key,
            ),
        )
    )


def _review_counts(
    items: tuple[DashboardReviewItem, ...],
) -> DashboardReviewCounts:
    return DashboardReviewCounts(
        total=len(items),
        by_severity=tuple(
            DashboardReviewCount(
                key=severity.value,
                count=sum(item.severity is severity for item in items),
            )
            for severity in ReviewItemSeverity
        ),
        by_category=tuple(
            DashboardReviewCount(
                key=category.value,
                count=sum(item.category is category for item in items),
            )
            for category in ReviewItemCategory
        ),
    )
