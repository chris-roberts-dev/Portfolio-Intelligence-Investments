"""Integration-style tests for owned-portfolio analytics orchestration."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.contracts import MarketBarBatchResult, MarketBarStatus
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.services import analytics
from apps.portfolios.services.analytics import (
    PortfolioAnalyticsWarningCode,
    analyze_owned_portfolio,
)
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
    TradingSessionCalendar,
)
from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.performance.time_weighted import (
    DailyPortfolioReturn,
    TimeWeightedReturnResult,
)
from portfolio_engine.portfolio.allocation import (
    PortfolioAllocationResult,
    SecurityAllocation,
)


class UnusedTradingCalendar:
    """Calendar boundary unused because valuation services are patched."""

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        del as_of_date, count
        raise AssertionError("trading calendar must not be called")


def dependencies() -> tuple[
    AssetResolver,
    MarketDataProvider,
    TradingSessionCalendar,
]:
    return (
        cast(AssetResolver, object()),
        cast(MarketDataProvider, object()),
        cast(TradingSessionCalendar, UnusedTradingCalendar()),
    )


def allocation(
    first_asset_id: UUID,
    second_asset_id: UUID,
) -> PortfolioAllocationResult:
    return PortfolioAllocationResult(
        positions=(
            SecurityAllocation(
                asset_id=first_asset_id,
                market_value=60.0,
                weight=0.60,
            ),
            SecurityAllocation(
                asset_id=second_asset_id,
                market_value=40.0,
                weight=0.40,
            ),
        ),
        cash_value=0.0,
        cash_weight=0.0,
        total_market_value=100.0,
        weight_sum=1.0,
        weight_sum_tolerance=WEIGHT_SUM_TOLERANCE,
    )


def twr_result(
    *,
    start: date,
    daily_returns: tuple[float, ...],
) -> TimeWeightedReturnResult:
    daily: list[DailyPortfolioReturn] = []
    prior_value = 100.0

    for index, simple_return in enumerate(
        daily_returns,
        start=1,
    ):
        ending_value = prior_value * (1.0 + simple_return)
        daily.append(
            DailyPortfolioReturn(
                valuation_date=start + timedelta(days=index),
                prior_portfolio_value=prior_value,
                ending_portfolio_value=ending_value,
                net_external_flow=0.0,
                simple_return=simple_return,
            )
        )
        prior_value = ending_value

    growth = math.prod(1.0 + simple_return for simple_return in daily_returns)

    return TimeWeightedReturnResult(
        period_start=start,
        period_end=start + timedelta(days=len(daily_returns)),
        daily_returns=tuple(daily),
        cumulative_return=growth - 1.0,
    )


def benchmark_bars(
    *,
    asset_id: UUID,
    start: date,
    portfolio_returns: tuple[float, ...],
    retrieved_at: datetime,
) -> tuple[PriceBar, ...]:
    price = 100.0
    bars = [
        PriceBar(
            asset_id=asset_id,
            trade_date=start,
            open=price,
            high=price,
            low=price,
            close=price,
            adjusted_close=price,
            volume=1000,
            source="mock",
            retrieved_at=retrieved_at,
        )
    ]

    for index, portfolio_return in enumerate(
        portfolio_returns,
        start=1,
    ):
        price *= 1.0 + 2.0 * portfolio_return
        bars.append(
            PriceBar(
                asset_id=asset_id,
                trade_date=start + timedelta(days=index),
                open=price,
                high=price,
                low=price,
                close=price,
                adjusted_close=price,
                volume=1000,
                source="mock",
                retrieved_at=retrieved_at,
            )
        )

    return tuple(bars)


@pytest.mark.django_db
def test_analytics_service_composes_phase3_metrics_and_benchmark_beta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="analytics-owner@example.com",
        password="test-password-123",
    )
    benchmark = Asset.objects.create(
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_type=AssetType.ETF,
        exchange="NYSEARCA",
    )
    first_asset = uuid4()
    second_asset = uuid4()
    portfolio_id = uuid4()
    start = date(2026, 1, 1)
    returns = tuple((0.003, -0.001, 0.002, -0.002)[index % 4] for index in range(60))
    twr = twr_result(
        start=start,
        daily_returns=returns,
    )
    valuation_times = tuple(
        datetime.combine(
            start + timedelta(days=index),
            datetime.min.time(),
            tzinfo=UTC,
        )
        for index in range(61)
    )
    performance = SimpleNamespace(
        twr=twr,
        warnings=(),
        provenance=SimpleNamespace(
            portfolio_id=portfolio_id,
            benchmark_asset_id=benchmark.id,
            provider="mock",
            retrieved_at=datetime(2026, 3, 2, tzinfo=UTC),
            price_field="adjusted_close",
            period_start=twr.period_start,
            period_end=twr.period_end,
        ),
    )
    current_allocation = allocation(
        first_asset,
        second_asset,
    )
    current = SimpleNamespace(
        is_complete=True,
        allocation=current_allocation,
    )

    monkeypatch.setattr(
        analytics,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: performance,
    )
    monkeypatch.setattr(
        analytics,
        "value_owned_portfolio",
        lambda **_kwargs: current,
    )

    retrieved_at = datetime(2026, 3, 2, tzinfo=UTC)
    bars = benchmark_bars(
        asset_id=benchmark.id,
        start=start,
        portfolio_returns=returns,
        retrieved_at=retrieved_at,
    )

    def executor(
        *args: object,
        **kwargs: object,
    ) -> MarketBarBatchResult:
        del args, kwargs
        return cast(
            MarketBarBatchResult,
            SimpleNamespace(
                results=(
                    SimpleNamespace(
                        symbol="SPY",
                        status=MarketBarStatus.SUCCEEDED,
                        bars=bars,
                        warnings=(),
                    ),
                ),
                meta=SimpleNamespace(
                    provider="mock",
                    retrieved_at=retrieved_at,
                ),
                row_count=len(bars),
            ),
        )

    resolver, provider, trading_calendar = dependencies()
    result = analyze_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        rolling_window_size=20,
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert result.observations == 60
    assert result.cumulative_return == pytest.approx(twr.cumulative_return)
    assert result.cagr is not None
    assert result.annualized_volatility is not None
    assert result.sharpe is not None
    assert result.sharpe.value is not None
    assert result.sortino is not None
    assert result.sortino.value is not None
    assert result.maximum_drawdown is not None

    assert result.beta is not None
    assert result.beta.value == pytest.approx(0.5)
    assert result.beta.observations == 60
    assert result.benchmark_observations == 60

    assert result.benchmark_correlation is not None
    assert result.benchmark_correlation.value == pytest.approx(1.0)
    assert result.benchmark_correlation.observations == 60

    assert result.rolling_return_window == 20
    assert len(result.rolling_returns) == 41
    assert result.rolling_returns[0].period_end == start + timedelta(days=20)
    assert result.rolling_returns[-1].period_end == start + timedelta(days=60)

    assert result.current_allocation is current_allocation
    assert result.concentration is not None
    assert result.concentration.largest_position_weight == pytest.approx(0.60)
    assert result.concentration.herfindahl_hirschman_index == pytest.approx(0.52)

    assert result.provenance.data_source == "mock"
    assert result.provenance.price_field == "adjusted_close"
    assert result.provenance.benchmark == "SPY"
    assert result.provenance.period_start == twr.period_start
    assert result.provenance.period_end == twr.period_end


@pytest.mark.django_db
def test_analytics_service_surfaces_application_minimum_history_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="analytics-short-history@example.com",
        password="test-password-123",
    )
    first_asset = uuid4()
    second_asset = uuid4()
    portfolio_id = uuid4()
    start = date(2026, 1, 1)
    returns = (0.01, -0.005, 0.002, 0.003, -0.001)
    twr = twr_result(
        start=start,
        daily_returns=returns,
    )
    valuation_times = tuple(
        datetime.combine(
            start + timedelta(days=index),
            datetime.min.time(),
            tzinfo=UTC,
        )
        for index in range(len(returns) + 1)
    )
    performance = SimpleNamespace(
        twr=twr,
        warnings=(),
        provenance=SimpleNamespace(
            portfolio_id=portfolio_id,
            benchmark_asset_id=None,
            provider="mock",
            retrieved_at=None,
            price_field="adjusted_close",
            period_start=twr.period_start,
            period_end=twr.period_end,
        ),
    )
    current = SimpleNamespace(
        is_complete=True,
        allocation=allocation(
            first_asset,
            second_asset,
        ),
    )

    monkeypatch.setattr(
        analytics,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: performance,
    )
    monkeypatch.setattr(
        analytics,
        "value_owned_portfolio",
        lambda **_kwargs: current,
    )

    resolver, provider, trading_calendar = dependencies()
    result = analyze_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=cast(
            MarketBarQueryExecutor,
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("benchmark request must not execute")
            ),
        ),
    )

    assert result.cumulative_return is not None
    assert result.cagr is not None
    assert result.maximum_drawdown is not None
    assert result.annualized_volatility is None
    assert result.sharpe is None
    assert result.sortino is None
    assert result.beta is None

    warning_codes = {warning.code for warning in result.warnings}
    assert PortfolioAnalyticsWarningCode.INSUFFICIENT_HISTORY in warning_codes
    assert PortfolioAnalyticsWarningCode.BENCHMARK_NOT_CONFIGURED in warning_codes
    assert result.provenance.warnings


@pytest.mark.django_db
def test_analytics_service_reports_insufficient_explicit_rolling_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="analytics-rolling-short@example.com",
        password="test-password-123",
    )
    portfolio_id = uuid4()
    first_asset = uuid4()
    second_asset = uuid4()
    start = date(2026, 1, 1)
    returns = (0.01, -0.005, 0.002, 0.003, -0.001)
    twr = twr_result(
        start=start,
        daily_returns=returns,
    )
    valuation_times = tuple(
        datetime.combine(
            start + timedelta(days=index),
            datetime.min.time(),
            tzinfo=UTC,
        )
        for index in range(len(returns) + 1)
    )
    performance = SimpleNamespace(
        twr=twr,
        warnings=(),
        provenance=SimpleNamespace(
            portfolio_id=portfolio_id,
            benchmark_asset_id=None,
            provider="mock",
            retrieved_at=None,
            price_field="adjusted_close",
            period_start=twr.period_start,
            period_end=twr.period_end,
        ),
    )
    current = SimpleNamespace(
        is_complete=True,
        allocation=allocation(
            first_asset,
            second_asset,
        ),
    )

    monkeypatch.setattr(
        analytics,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: performance,
    )
    monkeypatch.setattr(
        analytics,
        "value_owned_portfolio",
        lambda **_kwargs: current,
    )

    resolver, provider, trading_calendar = dependencies()
    result = analyze_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        rolling_window_size=10,
        executor=cast(
            MarketBarQueryExecutor,
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("benchmark request must not execute")
            ),
        ),
    )

    assert result.rolling_return_window == 10
    assert result.rolling_returns == ()

    warning_codes = {warning.code for warning in result.warnings}
    assert PortfolioAnalyticsWarningCode.INSUFFICIENT_ROLLING_HISTORY in warning_codes
