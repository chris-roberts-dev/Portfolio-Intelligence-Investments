"""Focused aggregation tests for dashboard review items."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

from apps.portfolios.services.analytics import (
    PortfolioAnalyticsResult,
    PortfolioAnalyticsWarning,
    PortfolioAnalyticsWarningCode,
)
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentValuationWarning,
    CurrentValuationWarningCode,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceWarning,
    DailyPerformanceWarningCode,
    DailyPortfolioPerformanceResult,
)
from apps.portfolios.services.dashboard_review_items import (
    ReviewDrilldownResource,
    ReviewItemCategory,
    ReviewItemSeverity,
    aggregate_dashboard_review_items,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001401")
A_ID = UUID("00000000-0000-0000-0000-000000001411")
B_ID = UUID("00000000-0000-0000-0000-000000001412")

T0 = datetime(2026, 9, 1, 23, tzinfo=UTC)
T1 = datetime(2026, 9, 15, 23, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 15, 23, 30, tzinfo=UTC)


def sources() -> tuple[
    CurrentPortfolioValuationResult,
    DailyPortfolioPerformanceResult,
    PortfolioAnalyticsResult,
]:
    current = cast(
        CurrentPortfolioValuationResult,
        SimpleNamespace(
            is_complete=False,
            warnings=(
                CurrentValuationWarning(
                    code=CurrentValuationWarningCode.STALE_PRICE_USED,
                    message="AAPL uses a stale current price.",
                    asset_id=A_ID,
                    symbol="AAPL",
                ),
                CurrentValuationWarning(
                    code=CurrentValuationWarningCode.PRICE_PROVIDER_FAILED,
                    message="Provider failed for MSFT.",
                    asset_id=B_ID,
                    symbol="MSFT",
                ),
            ),
            provenance=SimpleNamespace(
                provider="mock",
                as_of=CALCULATED_AT,
                retrieved_at=CALCULATED_AT,
            ),
        ),
    )
    performance = cast(
        DailyPortfolioPerformanceResult,
        SimpleNamespace(
            warnings=(
                DailyPerformanceWarning(
                    code=DailyPerformanceWarningCode.PRICE_NO_DATA,
                    message="AAPL has no historical observation.",
                    valuation_at=T1,
                    asset_id=A_ID,
                    symbol="AAPL",
                ),
                DailyPerformanceWarning(
                    code=DailyPerformanceWarningCode.TWR_UNDEFINED,
                    message="TWR is undefined for the selected range.",
                    valuation_at=T1,
                ),
            ),
            provenance=SimpleNamespace(
                provider="mock",
                retrieved_at=T1,
            ),
        ),
    )
    analytics = cast(
        PortfolioAnalyticsResult,
        SimpleNamespace(
            warnings=(
                PortfolioAnalyticsWarning(
                    code=PortfolioAnalyticsWarningCode.SOURCE_WARNING,
                    message="AAPL has no historical observation.",
                ),
                PortfolioAnalyticsWarning(
                    code=PortfolioAnalyticsWarningCode.INSUFFICIENT_HISTORY,
                    message="Insufficient observations.",
                    observations=10,
                ),
                PortfolioAnalyticsWarning(
                    code=(PortfolioAnalyticsWarningCode.BENCHMARK_NOT_CONFIGURED),
                    message="Portfolio has no benchmark.",
                ),
                PortfolioAnalyticsWarning(
                    code=(PortfolioAnalyticsWarningCode.BENCHMARK_PROVIDER_FAILED),
                    message="Benchmark provider failed.",
                    observations=0,
                ),
            ),
            provenance=SimpleNamespace(
                data_source="mock",
                as_of_date=T1.date(),
                engine_version="0.1.0.dev0",
            ),
        ),
    )

    return current, performance, analytics


def test_review_items_aggregate_stable_counts_without_double_counting() -> None:
    current, performance, analytics = sources()

    result = aggregate_dashboard_review_items(
        portfolio_id=PORTFOLIO_ID,
        base_currency="USD",
        requested_start=date(2026, 9, 1),
        requested_end=date(2026, 9, 16),
        valuation_times=(T0, T1),
        current=current,
        performance=performance,
        analytics=analytics,
        calculated_at=CALCULATED_AT,
    )

    assert result.counts.total == 7
    assert result.filtered_count == 7

    severity_counts = {item.key: item.count for item in result.counts.by_severity}
    assert severity_counts == {
        "ERROR": 4,
        "WARNING": 3,
        "INFO": 0,
    }

    category_counts = {item.key: item.count for item in result.counts.by_category}
    assert category_counts == {
        "MARKET_DATA": 1,
        "DATA_COVERAGE": 1,
        "PROVIDER": 2,
        "VALUATION": 1,
        "ANALYTICS": 2,
    }

    codes = tuple(item.code for item in result.items)

    assert "SOURCE_WARNING" not in codes
    assert "BENCHMARK_NOT_CONFIGURED" not in codes
    assert codes.count("PRICE_NO_DATA") == 1
    assert "CURRENT_VALUATION_INCOMPLETE" in codes


def test_review_filter_preserves_unfiltered_counts_and_drilldown_context() -> None:
    current, performance, analytics = sources()

    result = aggregate_dashboard_review_items(
        portfolio_id=PORTFOLIO_ID,
        base_currency="USD",
        requested_start=date(2026, 9, 1),
        requested_end=date(2026, 9, 16),
        valuation_times=(T0, T1),
        current=current,
        performance=performance,
        analytics=analytics,
        calculated_at=CALCULATED_AT,
        category=ReviewItemCategory.PROVIDER,
    )

    assert result.counts.total == 7
    assert result.filtered_count == 2
    assert all(item.category is ReviewItemCategory.PROVIDER for item in result.items)

    current_provider_item = next(
        item for item in result.items if item.code == "PRICE_PROVIDER_FAILED"
    )

    assert current_provider_item.severity is ReviewItemSeverity.ERROR
    assert current_provider_item.drilldown.resource is ReviewDrilldownResource.HOLDINGS
    assert current_provider_item.drilldown.portfolio_id == PORTFOLIO_ID
    assert current_provider_item.drilldown.asset_id == B_ID
    assert current_provider_item.drilldown.symbol == "MSFT"
    assert current_provider_item.drilldown.requested_start == date(
        2026,
        9,
        1,
    )
