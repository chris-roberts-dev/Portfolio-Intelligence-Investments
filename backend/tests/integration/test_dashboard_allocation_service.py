"""Integration coverage for P0 dashboard allocation composition."""

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
from apps.portfolios.models import Portfolio
from apps.portfolios.services import dashboard_allocation
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentPositionPrice,
    CurrentValuationProvenance,
    TradingSessionCalendar,
)
from apps.portfolios.services.dashboard_allocation import (
    DashboardAllocationUnavailableReason,
    build_owned_portfolio_dashboard_allocation,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)
from apps.portfolios.services.ledger import (
    LedgerReplayResult,
    PositionQuantity,
)
from portfolio_engine.portfolio.allocation import (
    PortfolioAllocationResult,
    SecurityAllocation,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001201")
STOCK_A_ID = UUID("00000000-0000-0000-0000-000000001211")
STOCK_B_ID = UUID("00000000-0000-0000-0000-000000001212")
ETF_ID = UUID("00000000-0000-0000-0000-000000001213")

AS_OF = datetime(2026, 9, 15, 21, tzinfo=UTC)


class UnusedTradingCalendar:
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
        cast(
            TradingSessionCalendar,
            UnusedTradingCalendar(),
        ),
    )


def create_asset(
    *,
    asset_id: UUID,
    symbol: str,
    asset_type: AssetType,
) -> Asset:
    return Asset.objects.create(
        id=asset_id,
        symbol=symbol,
        name=f"{symbol} Security",
        asset_type=asset_type,
        exchange="NYSE",
    )


def ledger() -> LedgerReplayResult:
    return LedgerReplayResult(
        portfolio_id=PORTFOLIO_ID,
        as_of=AS_OF,
        cash_balance=Decimal("100"),
        positions=(
            PositionQuantity(
                asset_id=STOCK_A_ID,
                quantity=Decimal("4"),
            ),
            PositionQuantity(
                asset_id=STOCK_B_ID,
                quantity=Decimal("2"),
            ),
            PositionQuantity(
                asset_id=ETF_ID,
                quantity=Decimal("3"),
            ),
        ),
        cash_flows=(),
        net_external_cash_flow=Decimal("1000"),
        net_internal_cash_flow=Decimal("-900"),
        transaction_count=4,
    )


def complete_current() -> CurrentPortfolioValuationResult:
    return CurrentPortfolioValuationResult(
        ledger=ledger(),
        provenance=CurrentValuationProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=None,
            provider="mock",
            as_of=AS_OF,
            retrieved_at=AS_OF,
            price_field="close",
        ),
        prices=(
            CurrentPositionPrice(
                asset_id=STOCK_A_ID,
                symbol="AAA",
                quantity=Decimal("4"),
                trade_date=AS_OF.date(),
                raw_close=Decimal("100"),
                stale_trading_sessions=0,
            ),
            CurrentPositionPrice(
                asset_id=STOCK_B_ID,
                symbol="BBB",
                quantity=Decimal("2"),
                trade_date=AS_OF.date(),
                raw_close=Decimal("100"),
                stale_trading_sessions=0,
            ),
            CurrentPositionPrice(
                asset_id=ETF_ID,
                symbol="ETF",
                quantity=Decimal("3"),
                trade_date=AS_OF.date(),
                raw_close=Decimal("100"),
                stale_trading_sessions=0,
            ),
        ),
        warnings=(),
        is_complete=True,
        valuation=None,
        allocation=PortfolioAllocationResult(
            positions=(
                SecurityAllocation(
                    asset_id=STOCK_A_ID,
                    market_value=400.0,
                    weight=0.4,
                ),
                SecurityAllocation(
                    asset_id=STOCK_B_ID,
                    market_value=200.0,
                    weight=0.2,
                ),
                SecurityAllocation(
                    asset_id=ETF_ID,
                    market_value=300.0,
                    weight=0.3,
                ),
            ),
            cash_value=100.0,
            cash_weight=0.1,
            total_market_value=1000.0,
            weight_sum=1.0,
            weight_sum_tolerance=1e-8,
        ),
    )


@pytest.mark.django_db
def test_allocation_groups_authoritative_weights_and_exact_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="allocation-service@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Allocation Portfolio",
    )
    create_asset(
        asset_id=STOCK_A_ID,
        symbol="AAA",
        asset_type=AssetType.STOCK,
    )
    create_asset(
        asset_id=STOCK_B_ID,
        symbol="BBB",
        asset_type=AssetType.STOCK,
    )
    create_asset(
        asset_id=ETF_ID,
        symbol="ETF",
        asset_type=AssetType.ETF,
    )

    monkeypatch.setattr(
        dashboard_allocation,
        "value_owned_portfolio",
        lambda **_kwargs: complete_current(),
    )

    resolver, provider, calendar = dependencies()
    result = build_owned_portfolio_dashboard_allocation(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=AS_OF,
    )

    assert result.allocation_available is True
    assert result.unavailable_reason is None
    assert tuple(group.key for group in result.groups) == (
        "STOCK",
        "ETF",
        "CASH",
    )

    stocks, etfs, cash = result.groups

    assert stocks.label == "Stocks"
    assert stocks.asset_count == 2
    assert stocks.market_value == Decimal("600")
    assert stocks.weight == pytest.approx(0.6)

    assert etfs.asset_count == 1
    assert etfs.market_value == Decimal("300")
    assert etfs.weight == pytest.approx(0.3)

    assert cash.is_cash is True
    assert cash.market_value == Decimal("100")
    assert cash.weight == pytest.approx(0.1)

    assert result.totals.invested_value == Decimal("900")
    assert result.totals.cash_value == Decimal("100")
    assert result.totals.total_market_value == Decimal("1000")
    assert result.totals.invested_weight == pytest.approx(0.9)
    assert result.totals.cash_weight == pytest.approx(0.1)

    assert result.data_quality is PerformanceDataQualityState.CURRENT
    assert result.provenance.grouping_dimension == "ASSET_CLASS"
    assert result.provenance.supported_grouping_dimensions == ("ASSET_CLASS",)
    assert result.provenance.other_grouping_applied is False
    assert result.provenance.other_grouping_threshold is None


@pytest.mark.django_db
def test_incomplete_current_valuation_never_exposes_partial_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="allocation-partial@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Partial Allocation",
    )

    partial = CurrentPortfolioValuationResult(
        ledger=ledger(),
        provenance=CurrentValuationProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=None,
            provider="mock",
            as_of=AS_OF,
            retrieved_at=AS_OF,
            price_field="close",
        ),
        prices=(),
        warnings=(),
        is_complete=False,
        valuation=None,
        allocation=None,
    )

    monkeypatch.setattr(
        dashboard_allocation,
        "value_owned_portfolio",
        lambda **_kwargs: partial,
    )

    resolver, provider, calendar = dependencies()
    result = build_owned_portfolio_dashboard_allocation(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=calendar,
        calculated_at=AS_OF,
    )

    assert result.allocation_available is False
    assert result.groups == ()
    assert result.totals.total_market_value is None
    assert result.totals.invested_value is None
    assert result.totals.cash_value == Decimal("100")
    assert result.totals.invested_weight is None
    assert result.totals.cash_weight is None
    assert (
        result.unavailable_reason
        is DashboardAllocationUnavailableReason.CURRENT_VALUATION_INCOMPLETE
    )
    assert result.data_quality is PerformanceDataQualityState.PARTIAL
