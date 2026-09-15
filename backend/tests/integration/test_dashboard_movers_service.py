"""Integration-style coverage for dashboard mover orchestration."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services import dashboard_movers
from apps.portfolios.services.current_valuation import TradingSessionCalendar
from apps.portfolios.services.daily_performance import (
    DailyAssetValuation,
    DailyPerformanceProvenance,
    DailyPortfolioPerformanceResult,
    DailyPortfolioValuation,
)
from apps.portfolios.services.dashboard_holdings import (
    DashboardHolding,
    DashboardHoldingsProvenance,
    DashboardHoldingsResult,
    HoldingMetricUnavailableReason,
)
from apps.portfolios.services.dashboard_movers import (
    DashboardMover,
    PerformanceDataQualityState,
    _internal_asset_cash_flows_by_period,
    _rank_positive,
    build_owned_portfolio_dashboard_movers,
)
from portfolio_engine.performance.time_weighted import (
    DailyPortfolioReturn,
    TimeWeightedReturnResult,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000000701")
A_ID = UUID("00000000-0000-0000-0000-000000000711")
B_ID = UUID("00000000-0000-0000-0000-000000000712")
C_ID = UUID("00000000-0000-0000-0000-000000000713")

T0 = datetime(2026, 1, 2, 23, tzinfo=UTC)
T1 = datetime(2026, 1, 5, 23, tzinfo=UTC)
T2 = datetime(2026, 1, 6, 23, tzinfo=UTC)
TIMES = (T0, T1, T2)
CALCULATED_AT = datetime(2026, 1, 6, 23, 30, tzinfo=UTC)


class UnusedCalendar:
    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        del as_of_date, count
        raise AssertionError("calendar should not be called")


def dependencies() -> tuple[
    AssetResolver,
    MarketDataProvider,
    TradingSessionCalendar,
]:
    return (
        cast(AssetResolver, object()),
        cast(MarketDataProvider, object()),
        cast(TradingSessionCalendar, UnusedCalendar()),
    )


def create_asset(
    *,
    asset_id: UUID,
    symbol: str,
) -> Asset:
    return Asset.objects.create(
        id=asset_id,
        symbol=symbol,
        name=f"{symbol} Security",
        asset_type=AssetType.STOCK,
        exchange="NYSE",
    )


def holding(
    *,
    asset: Asset,
    selected_return: float,
    price: str,
    weight: float,
) -> DashboardHolding:
    return DashboardHolding(
        asset_id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_type=asset.asset_type,
        currency=asset.currency,
        quantity=Decimal("1"),
        current_price=Decimal(price),
        current_price_date=T2.date(),
        current_price_retrieved_at=CALCULATED_AT,
        stale_trading_sessions=0,
        market_value=Decimal(price),
        weight=weight,
        weight_unavailable_reason=None,
        selected_period_return=selected_return,
        selected_period_return_unavailable_reason=None,
        contribution_to_return=None,
        contribution_unavailable_reason=(
            HoldingMetricUnavailableReason.CONTRIBUTION_NOT_CALCULATED
        ),
        sparkline=(),
        data_quality=PerformanceDataQualityState.CURRENT,
        warnings=(),
    )


def position(
    asset: Asset,
    value: str,
) -> DailyAssetValuation:
    market_value = Decimal(value)
    return DailyAssetValuation(
        asset_id=asset.id,
        symbol=asset.symbol,
        quantity=Decimal("1"),
        price_date=T0.date(),
        adjusted_close=market_value,
        market_value=market_value,
        stale_trading_sessions=0,
    )


def performance(
    *,
    a: Asset,
    b: Asset,
    c: Asset,
) -> DailyPortfolioPerformanceResult:
    valuations = (
        DailyPortfolioValuation(
            as_of=T0,
            cash_balance=Decimal("0"),
            security_value=Decimal("100"),
            total_value=Decimal("100"),
            net_external_flow=Decimal("0"),
            positions=(
                position(a, "40"),
                position(b, "30"),
                position(c, "30"),
            ),
            warnings=(),
            is_complete=True,
        ),
        DailyPortfolioValuation(
            as_of=T1,
            cash_balance=Decimal("0"),
            security_value=Decimal("104"),
            total_value=Decimal("104"),
            net_external_flow=Decimal("0"),
            positions=(
                position(a, "44"),
                position(b, "27"),
                position(c, "33"),
            ),
            warnings=(),
            is_complete=True,
        ),
        DailyPortfolioValuation(
            as_of=T2,
            cash_balance=Decimal("0"),
            security_value=Decimal("108"),
            total_value=Decimal("108"),
            net_external_flow=Decimal("0"),
            positions=(
                position(a, "46"),
                position(b, "27"),
                position(c, "35"),
            ),
            warnings=(),
            is_complete=True,
        ),
    )
    twr = TimeWeightedReturnResult(
        period_start=T0.date(),
        period_end=T2.date(),
        daily_returns=(
            DailyPortfolioReturn(
                valuation_date=T1.date(),
                prior_portfolio_value=100.0,
                ending_portfolio_value=104.0,
                net_external_flow=0.0,
                simple_return=0.04,
            ),
            DailyPortfolioReturn(
                valuation_date=T2.date(),
                prior_portfolio_value=104.0,
                ending_portfolio_value=108.0,
                net_external_flow=0.0,
                simple_return=4.0 / 104.0,
            ),
        ),
        cumulative_return=0.08,
    )
    return DailyPortfolioPerformanceResult(
        valuations=valuations,
        twr=twr,
        warnings=(),
        provenance=DailyPerformanceProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=None,
            provider="mock",
            retrieved_at=CALCULATED_AT,
            price_field="adjusted_close",
            period_start=T0.date(),
            period_end=T2.date(),
        ),
    )


@pytest.mark.django_db
def test_movers_rank_price_returns_and_linked_contributions_server_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="movers@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Movers Portfolio",
    )
    a = create_asset(asset_id=A_ID, symbol="AAA")
    b = create_asset(asset_id=B_ID, symbol="BBB")
    c = create_asset(asset_id=C_ID, symbol="CCC")
    holdings = DashboardHoldingsResult(
        holdings=(
            holding(
                asset=a,
                selected_return=0.15,
                price="46",
                weight=46.0 / 108.0,
            ),
            holding(
                asset=b,
                selected_return=-0.10,
                price="27",
                weight=27.0 / 108.0,
            ),
            holding(
                asset=c,
                selected_return=5.0 / 30.0,
                price="35",
                weight=35.0 / 108.0,
            ),
        ),
        data_quality=PerformanceDataQualityState.CURRENT,
        warnings=(),
        provenance=DashboardHoldingsProvenance(
            portfolio_id=portfolio.id,
            base_currency="USD",
            provider="mock",
            requested_start=date(2026, 1, 2),
            requested_end_exclusive=date(2026, 1, 7),
            effective_start=T0.date(),
            effective_end_exclusive=date(2026, 1, 7),
            current_price_as_of=CALCULATED_AT,
            period_data_as_of=CALCULATED_AT,
            calculated_at=CALCULATED_AT,
            current_price_field="close",
            period_price_field="adjusted_close",
        ),
    )
    perf = performance(a=a, b=b, c=c)

    monkeypatch.setattr(
        dashboard_movers,
        "build_owned_portfolio_dashboard_holdings",
        lambda **_kwargs: holdings,
    )
    monkeypatch.setattr(
        dashboard_movers,
        "calculate_owned_portfolio_daily_performance",
        lambda **_kwargs: perf,
    )

    resolver, provider, calendar = dependencies()
    result = build_owned_portfolio_dashboard_movers(
        user=user,
        portfolio_id=portfolio.id,
        valuation_times=TIMES,
        requested_start=date(2026, 1, 2),
        requested_end=date(2026, 1, 7),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=CALCULATED_AT,
        limit=2,
    )

    assert tuple(item.symbol for item in result.top_gainers) == (
        "CCC",
        "AAA",
    )
    assert tuple(item.symbol for item in result.top_losers) == ("BBB",)
    assert tuple(item.symbol for item in result.largest_contributors) == ("AAA", "CCC")
    assert tuple(item.symbol for item in result.largest_detractors) == ("BBB",)

    assert result.largest_contributors[0].contribution_to_return == pytest.approx(0.06)
    assert result.largest_contributors[1].contribution_to_return == pytest.approx(0.05)
    assert result.largest_detractors[0].contribution_to_return == pytest.approx(-0.03)
    assert result.reconciliation.cumulative_return == pytest.approx(0.08)
    assert result.reconciliation.asset_contribution_total == pytest.approx(0.08)
    assert result.reconciliation.unattributed_contribution == pytest.approx(0.0)
    assert result.reconciliation.reconciliation_error == pytest.approx(0.0)
    assert result.provenance.attribution_method == "ASSET_PNL_WEALTH_LINKED_V1"


@pytest.mark.django_db
def test_internal_asset_cash_flow_mapping_matches_ledger_cash_semantics() -> None:
    user = User.objects.create_user(
        email="movers-cash@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=user,
        name="Mover Cash Flows",
    )
    a = create_asset(asset_id=A_ID, symbol="AAA")
    b = create_asset(asset_id=B_ID, symbol="BBB")
    c = create_asset(asset_id=C_ID, symbol="CCC")

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=a,
        occurred_at=datetime(2026, 1, 5, 10, tzinfo=UTC),
        source_sequence=1,
        quantity=Decimal("2"),
        price=Decimal("10"),
        fees=Decimal("1"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.SELL,
        asset=b,
        occurred_at=datetime(2026, 1, 5, 11, tzinfo=UTC),
        source_sequence=2,
        quantity=Decimal("1"),
        price=Decimal("20"),
        fees=Decimal("2"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DIVIDEND,
        asset=c,
        occurred_at=datetime(2026, 1, 5, 12, tzinfo=UTC),
        source_sequence=3,
        cash_amount=Decimal("5"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 1, 5, 13, tzinfo=UTC),
        source_sequence=4,
        cash_amount=Decimal("100"),
    )

    flows = _internal_asset_cash_flows_by_period(
        portfolio=portfolio,
        valuation_times=TIMES,
    )

    assert flows == (
        {
            a.id: Decimal("-21"),
            b.id: Decimal("18"),
            c.id: Decimal("5"),
        },
        {},
    )


def test_positive_ranking_ties_use_symbol_then_internal_uuid() -> None:
    def ranked_mover(
        *,
        asset_id: UUID,
        symbol: str,
    ) -> DashboardMover:
        return DashboardMover(
            asset_id=asset_id,
            symbol=symbol,
            name=f"{symbol} Security",
            asset_type="STOCK",
            currency="USD",
            is_current_holding=True,
            quantity=Decimal("1"),
            current_price=Decimal("10"),
            current_price_date=T2.date(),
            current_price_retrieved_at=CALCULATED_AT,
            stale_trading_sessions=0,
            market_value=Decimal("10"),
            weight=0.1,
            selected_period_return=0.1,
            contribution_to_return=0.02,
            sparkline=(),
            data_quality=PerformanceDataQualityState.CURRENT,
            unavailable_reasons=(),
        )

    aaa_first = ranked_mover(
        asset_id=UUID("00000000-0000-0000-0000-000000000001"),
        symbol="AAA",
    )
    aaa_second = ranked_mover(
        asset_id=UUID("00000000-0000-0000-0000-000000000003"),
        symbol="AAA",
    )
    bbb = ranked_mover(
        asset_id=UUID("00000000-0000-0000-0000-000000000002"),
        symbol="BBB",
    )

    ranked = _rank_positive(
        (bbb, aaa_second, aaa_first),
        metric="contribution_to_return",
        limit=3,
    )

    assert tuple(item.asset_id for item in ranked) == (
        aaa_first.asset_id,
        aaa_second.asset_id,
        bbb.asset_id,
    )
