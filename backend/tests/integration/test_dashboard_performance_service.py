"""Integration-style tests for display-ready dashboard performance orchestration."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarInterval,
    MarketBarStatus,
    MarketBarSymbolResult,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.models import Portfolio
from apps.portfolios.services import dashboard_performance
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
    TradingSessionCalendar,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceProvenance,
    DailyPortfolioPerformanceResult,
    DailyPortfolioValuation,
)
from apps.portfolios.services.dashboard_performance import (
    DashboardPerformanceWarningCode,
    PerformanceDataQualityState,
    build_owned_portfolio_dashboard_performance,
)
from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.performance.time_weighted import (
    DailyPortfolioReturn,
    TimeWeightedReturnResult,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000000501")
BENCHMARK_ID = UUID("00000000-0000-0000-0000-000000000502")
RETRIEVED_AT = datetime(2026, 1, 6, 22, tzinfo=UTC)
CALCULATED_AT = datetime(2026, 1, 6, 23, tzinfo=UTC)

DATES = (
    date(2026, 1, 2),
    date(2026, 1, 5),
    date(2026, 1, 6),
)

TIMES = tuple(datetime(day.year, day.month, day.day, 23, tzinfo=UTC) for day in DATES)


class UnusedTradingCalendar:
    """Calendar boundary unused because daily performance is patched."""

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        del as_of_date, count
        raise AssertionError("calendar must not be called")


def dependencies() -> tuple[
    AssetResolver,
    MarketDataProvider,
    TradingSessionCalendar,
]:
    return (
        cast(AssetResolver, object()),
        cast(MarketDataProvider, object()),
        cast(
            TradingSessionCalendar,
            UnusedTradingCalendar(),
        ),
    )


def make_performance(
    *,
    benchmark_asset_id: UUID | None,
) -> DailyPortfolioPerformanceResult:
    valuations = (
        DailyPortfolioValuation(
            as_of=TIMES[0],
            cash_balance=Decimal("1000"),
            security_value=Decimal("0"),
            total_value=Decimal("1000"),
            net_external_flow=Decimal("0"),
            positions=(),
            warnings=(),
            is_complete=True,
        ),
        DailyPortfolioValuation(
            as_of=TIMES[1],
            cash_balance=Decimal("1200"),
            security_value=Decimal("0"),
            total_value=Decimal("1200"),
            net_external_flow=Decimal("100"),
            positions=(),
            warnings=(),
            is_complete=True,
        ),
        DailyPortfolioValuation(
            as_of=TIMES[2],
            cash_balance=Decimal("1260"),
            security_value=Decimal("0"),
            total_value=Decimal("1260"),
            net_external_flow=Decimal("0"),
            positions=(),
            warnings=(),
            is_complete=True,
        ),
    )
    twr = TimeWeightedReturnResult(
        period_start=DATES[0],
        period_end=DATES[-1],
        daily_returns=(
            DailyPortfolioReturn(
                valuation_date=DATES[1],
                prior_portfolio_value=1000.0,
                ending_portfolio_value=1200.0,
                net_external_flow=100.0,
                simple_return=0.10,
            ),
            DailyPortfolioReturn(
                valuation_date=DATES[2],
                prior_portfolio_value=1200.0,
                ending_portfolio_value=1260.0,
                net_external_flow=0.0,
                simple_return=0.05,
            ),
        ),
        cumulative_return=0.155,
    )
    return DailyPortfolioPerformanceResult(
        valuations=valuations,
        twr=twr,
        warnings=(),
        provenance=DailyPerformanceProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=benchmark_asset_id,
            provider="mock",
            retrieved_at=RETRIEVED_AT,
            price_field="adjusted_close",
            period_start=DATES[0],
            period_end=DATES[-1],
        ),
    )


def benchmark_bar(
    trade_date: date,
    adjusted_close: float,
) -> PriceBar:
    return PriceBar(
        asset_id=BENCHMARK_ID,
        trade_date=trade_date,
        open=adjusted_close,
        high=adjusted_close,
        low=adjusted_close,
        close=adjusted_close,
        adjusted_close=adjusted_close,
        volume=1000,
        source="mock",
        retrieved_at=RETRIEVED_AT,
    )


@pytest.mark.django_db
def test_dashboard_performance_exposes_flow_aware_summary_and_benchmark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="dashboard-performance@example.com",
        password="test-password-123",
    )
    benchmark = Asset.objects.create(
        id=BENCHMARK_ID,
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_type=AssetType.ETF,
        exchange="NYSEARCA",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Dashboard Portfolio",
        benchmark_asset=benchmark,
    )
    monkeypatch.setattr(
        dashboard_performance,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: make_performance(benchmark_asset_id=BENCHMARK_ID),
    )

    def executor(
        *_args: object,
        **_kwargs: object,
    ) -> MarketBarBatchResult:
        return MarketBarBatchResult(
            results=(
                MarketBarSymbolResult(
                    symbol="SPY",
                    asset_id=BENCHMARK_ID,
                    status=MarketBarStatus.SUCCEEDED,
                    bars=tuple(
                        benchmark_bar(day, price)
                        for day, price in zip(
                            DATES,
                            (100.0, 110.0, 115.0),
                            strict=True,
                        )
                    ),
                ),
            ),
            meta=MarketBarBatchMeta(
                provider="mock",
                retrieved_at=RETRIEVED_AT,
                interval=MarketBarInterval.DAILY,
                start=DATES[0],
                end=date(2026, 1, 7),
            ),
        )

    resolver, provider, calendar = dependencies()
    result = build_owned_portfolio_dashboard_performance(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        valuation_times=TIMES,
        requested_start=date(2026, 1, 1),
        requested_end=date(2026, 1, 7),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert result.summary.starting_value == Decimal("1000")
    assert result.summary.ending_value == Decimal("1260")
    assert result.summary.value_change == Decimal("260")
    assert result.summary.net_external_flow == Decimal("100")
    assert result.summary.investment_gain_loss == Decimal("160")
    assert result.summary.cumulative_return == pytest.approx(0.155)
    assert result.summary.benchmark_cumulative_return == pytest.approx(0.15)
    assert tuple(point.cumulative_return for point in result.points) == pytest.approx(
        (0.0, 0.10, 0.155)
    )
    assert tuple(point.cumulative_return for point in result.benchmark_points) == pytest.approx(
        (0.0, 0.10, 0.15)
    )
    assert result.portfolio_data_quality is PerformanceDataQualityState.CURRENT
    assert result.benchmark_data_quality is PerformanceDataQualityState.CURRENT
    assert result.provenance.base_currency == "USD"
    assert result.provenance.data_as_of == RETRIEVED_AT
    assert result.provenance.calculated_at == CALCULATED_AT
    assert result.provenance.benchmark_symbol == "SPY"


@pytest.mark.django_db
def test_benchmark_gap_remains_explicit_and_is_never_interpolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="dashboard-gap@example.com",
        password="test-password-123",
    )
    benchmark = Asset.objects.create(
        id=BENCHMARK_ID,
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_type=AssetType.ETF,
        exchange="NYSEARCA",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Dashboard Portfolio",
        benchmark_asset=benchmark,
    )
    monkeypatch.setattr(
        dashboard_performance,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: make_performance(benchmark_asset_id=BENCHMARK_ID),
    )

    def executor(
        *_args: object,
        **_kwargs: object,
    ) -> MarketBarBatchResult:
        return MarketBarBatchResult(
            results=(
                MarketBarSymbolResult(
                    symbol="SPY",
                    asset_id=BENCHMARK_ID,
                    status=MarketBarStatus.SUCCEEDED,
                    bars=(
                        benchmark_bar(DATES[0], 100.0),
                        benchmark_bar(DATES[2], 115.0),
                    ),
                ),
            ),
            meta=MarketBarBatchMeta(
                provider="mock",
                retrieved_at=RETRIEVED_AT,
                interval=MarketBarInterval.DAILY,
                start=DATES[0],
                end=date(2026, 1, 7),
            ),
        )

    resolver, provider, calendar = dependencies()
    result = build_owned_portfolio_dashboard_performance(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        valuation_times=TIMES,
        requested_start=date(2026, 1, 1),
        requested_end=date(2026, 1, 7),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert result.benchmark_points[1].adjusted_close is None
    assert result.benchmark_points[1].cumulative_return is None
    assert result.benchmark_points[1].data_quality is PerformanceDataQualityState.PARTIAL
    assert result.benchmark_points[2].cumulative_return == pytest.approx(0.15)
    assert result.benchmark_data_quality is PerformanceDataQualityState.PARTIAL
    assert any(
        warning.code == (DashboardPerformanceWarningCode.BENCHMARK_MISSING_OBSERVATION.value)
        for warning in result.warnings
    )
