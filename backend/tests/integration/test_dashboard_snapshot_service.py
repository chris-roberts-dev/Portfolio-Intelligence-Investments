"""Deterministic service tests for the canonical dashboard snapshot."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.models import Portfolio
from apps.portfolios.services import dashboard_snapshot
from apps.portfolios.services.analytics import PortfolioAnalyticsResult
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    MarketBarQueryExecutor,
    TradingSessionCalendar,
)
from apps.portfolios.services.daily_performance import (
    DailyPortfolioPerformanceResult,
)
from apps.portfolios.services.dashboard_allocation import (
    DashboardAllocationResult,
)
from apps.portfolios.services.dashboard_holdings import DashboardHoldingsResult
from apps.portfolios.services.dashboard_movers import DashboardMoversResult
from apps.portfolios.services.dashboard_performance import (
    DashboardPerformanceResult,
)
from apps.portfolios.services.dashboard_review_items import (
    DashboardReviewItemsResult,
)
from apps.portfolios.services.dashboard_snapshot import (
    DashboardSnapshotError,
    DashboardSnapshotModule,
    DashboardSnapshotModuleStatus,
    MemoizedMarketBarQueryExecutor,
    build_owned_portfolio_dashboard_snapshot,
)
from apps.portfolios.services.dashboard_summary import (
    DashboardPortfolioSummaryError,
    DashboardPortfolioSummaryResult,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001601")
T0 = datetime(2026, 9, 1, 23, tzinfo=UTC)
T1 = datetime(2026, 9, 15, 23, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 9, 16, 0, tzinfo=UTC)


def dependencies() -> tuple[
    AssetResolver,
    MarketDataProvider,
    TradingSessionCalendar,
]:
    return (
        cast(AssetResolver, object()),
        cast(MarketDataProvider, object()),
        cast(TradingSessionCalendar, object()),
    )


def source_results() -> tuple[
    CurrentPortfolioValuationResult,
    DailyPortfolioPerformanceResult,
    PortfolioAnalyticsResult,
]:
    current = cast(
        CurrentPortfolioValuationResult,
        SimpleNamespace(
            provenance=SimpleNamespace(retrieved_at=CALCULATED_AT),
        ),
    )
    performance = cast(
        DailyPortfolioPerformanceResult,
        SimpleNamespace(
            provenance=SimpleNamespace(retrieved_at=T1),
        ),
    )
    analytics = cast(
        PortfolioAnalyticsResult,
        SimpleNamespace(
            provenance=SimpleNamespace(as_of_date=T1.date()),
        ),
    )
    return current, performance, analytics


def install_successful_modules(
    monkeypatch: pytest.MonkeyPatch,
    *,
    captured: list[dict[str, object]],
) -> None:
    current, performance, analytics = source_results()
    monkeypatch.setattr(
        dashboard_snapshot,
        "value_owned_portfolio",
        lambda **_kwargs: current,
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: performance,
    )

    def record_result(
        result: object,
    ) -> object:
        def callback(**kwargs: object) -> object:
            captured.append(kwargs)
            return result

        return callback

    monkeypatch.setattr(
        dashboard_snapshot,
        "build_owned_portfolio_dashboard_summary",
        record_result(cast(DashboardPortfolioSummaryResult, object())),
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "build_owned_portfolio_dashboard_performance",
        record_result(cast(DashboardPerformanceResult, object())),
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "build_owned_portfolio_dashboard_allocation",
        record_result(cast(DashboardAllocationResult, object())),
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "build_owned_portfolio_dashboard_holdings",
        record_result(cast(DashboardHoldingsResult, object())),
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "build_owned_portfolio_dashboard_movers",
        record_result(cast(DashboardMoversResult, object())),
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "analyze_owned_portfolio",
        record_result(analytics),
    )
    monkeypatch.setattr(
        dashboard_snapshot,
        "aggregate_dashboard_review_items",
        record_result(cast(DashboardReviewItemsResult, object())),
    )


@pytest.mark.django_db
def test_snapshot_shares_cutoff_provider_range_and_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="snapshot-service@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Snapshot Portfolio",
    )
    captured: list[dict[str, object]] = []
    install_successful_modules(monkeypatch, captured=captured)
    resolver, provider, calendar = dependencies()

    result = build_owned_portfolio_dashboard_snapshot(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        valuation_times=(T0, T1),
        requested_start=T0.date(),
        requested_end=date(2026, 9, 16),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        movers_limit=5,
        risk_free_rate_annual=0.02,
        minimum_acceptable_return_annual=0.01,
    )

    assert result.is_complete is True
    assert result.snapshot.portfolio_id == PORTFOLIO_ID
    assert result.snapshot.provider == "mock"
    assert result.snapshot.valuation_cutoff == CALCULATED_AT
    assert result.snapshot.calculated_at == CALCULATED_AT
    assert result.snapshot.effective_start == T0.date()
    assert result.snapshot.effective_end_exclusive == date(2026, 9, 16)
    assert result.snapshot.current_data_as_of == CALCULATED_AT
    assert result.snapshot.historical_data_as_of == T1
    assert result.snapshot.analytics_as_of_date == T1.date()

    executors = {id(kwargs["executor"]) for kwargs in captured if "executor" in kwargs}
    assert len(executors) == 1

    calculated_ats = {kwargs["calculated_at"] for kwargs in captured if "calculated_at" in kwargs}
    assert calculated_ats == {CALCULATED_AT}

    providers = {kwargs["provider_name"] for kwargs in captured if "provider_name" in kwargs}
    assert providers == {"mock"}


@pytest.mark.django_db
def test_snapshot_identity_is_stable_for_same_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="snapshot-id@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Snapshot Identity",
    )
    captured: list[dict[str, object]] = []
    install_successful_modules(monkeypatch, captured=captured)
    resolver, provider, calendar = dependencies()

    first = build_owned_portfolio_dashboard_snapshot(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        valuation_times=(T0, T1),
        requested_start=T0.date(),
        requested_end=date(2026, 9, 16),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        movers_limit=5,
        risk_free_rate_annual=0.02,
        minimum_acceptable_return_annual=0.01,
    )
    second = build_owned_portfolio_dashboard_snapshot(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        valuation_times=(T0, T1),
        requested_start=T0.date(),
        requested_end=date(2026, 9, 16),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        movers_limit=5,
        risk_free_rate_annual=0.02,
        minimum_acceptable_return_annual=0.01,
    )

    assert first.snapshot.snapshot_id == second.snapshot.snapshot_id


@pytest.mark.django_db
def test_one_module_failure_remains_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="snapshot-partial@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Partial Snapshot",
    )
    captured: list[dict[str, object]] = []
    install_successful_modules(monkeypatch, captured=captured)

    def fail_summary(**_kwargs: object) -> DashboardPortfolioSummaryResult:
        raise DashboardPortfolioSummaryError("summary unavailable")

    monkeypatch.setattr(
        dashboard_snapshot,
        "build_owned_portfolio_dashboard_summary",
        fail_summary,
    )
    resolver, provider, calendar = dependencies()

    result = build_owned_portfolio_dashboard_snapshot(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        valuation_times=(T0, T1),
        requested_start=T0.date(),
        requested_end=date(2026, 9, 16),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        movers_limit=5,
        risk_free_rate_annual=0.02,
        minimum_acceptable_return_annual=0.01,
    )

    summary_state = next(
        state for state in result.modules if state.module is DashboardSnapshotModule.SUMMARY
    )

    assert result.is_complete is False
    assert result.summary is None
    assert summary_state.status is DashboardSnapshotModuleStatus.UNAVAILABLE
    assert summary_state.error_code == "SUMMARY_UNAVAILABLE"
    assert result.performance is not None
    assert result.analytics is not None


def test_snapshot_rejects_future_valuation_boundary() -> None:
    resolver, provider, calendar = dependencies()
    user = cast(User, object())

    with pytest.raises(
        DashboardSnapshotError,
        match="snapshot cutoff",
    ):
        build_owned_portfolio_dashboard_snapshot(
            user=user,
            portfolio_id=PORTFOLIO_ID,
            valuation_times=(
                T0,
                datetime(2026, 9, 16, 23, tzinfo=UTC),
            ),
            requested_start=T0.date(),
            requested_end=date(2026, 9, 17),
            provider_name="mock",
            resolver=resolver,
            provider=provider,
            trading_calendar=calendar,
            calculated_at=CALCULATED_AT,
            movers_limit=5,
            risk_free_rate_annual=0.02,
            minimum_acceptable_return_annual=0.01,
        )


def test_memoized_executor_executes_identical_query_only_once() -> None:
    query = normalize_market_bar_query(
        ("AAPL",),
        start=date(2026, 9, 1),
        end=date(2026, 9, 2),
        provider="mock",
    )
    expected = MarketBarBatchResult(
        results=(),
        meta=MarketBarBatchMeta(
            provider="mock",
            retrieved_at=CALCULATED_AT,
            interval=MarketBarInterval.DAILY,
            start=date(2026, 9, 1),
            end=date(2026, 9, 2),
        ),
    )
    calls = 0

    def delegate(
        _query: object,
        *,
        resolver: object,
        provider: object,
    ) -> MarketBarBatchResult:
        nonlocal calls
        del resolver, provider
        calls += 1
        return expected

    memoized = MemoizedMarketBarQueryExecutor(
        cast(MarketBarQueryExecutor, delegate),
    )
    resolver, provider, _calendar = dependencies()

    first = memoized(query, resolver=resolver, provider=provider)
    second = memoized(query, resolver=resolver, provider=provider)

    assert first is expected
    assert second is expected
    assert calls == 1
    assert memoized.executed_queries == 1
    assert memoized.reused_queries == 1
