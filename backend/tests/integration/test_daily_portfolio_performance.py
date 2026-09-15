"""Integration coverage for daily owned-portfolio performance."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.contracts import (
    MarketBarBatchResult,
    MarketBarStatus,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceWarningCode,
    calculate_owned_portfolio_daily_performance,
)
from portfolio_engine.contracts.market_data import PriceBar


class FixedTradingCalendar:
    """Deterministic trading calendar for performance tests."""

    def __init__(
        self,
        sessions: tuple[date, ...],
    ) -> None:
        self._sessions = sessions

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        eligible = tuple(session for session in self._sessions if session <= as_of_date)
        return eligible[-count:]


def dependencies() -> tuple[
    AssetResolver,
    MarketDataProvider,
]:
    return (
        cast(AssetResolver, object()),
        cast(MarketDataProvider, object()),
    )


def price_bar(
    *,
    asset_id: UUID,
    trade_date: date,
    raw_close: float,
    adjusted_close: float,
    retrieved_at: datetime,
) -> PriceBar:
    return PriceBar(
        asset_id=asset_id,
        trade_date=trade_date,
        open=raw_close,
        high=raw_close,
        low=raw_close,
        close=raw_close,
        adjusted_close=adjusted_close,
        volume=1000,
        source="mock",
        retrieved_at=retrieved_at,
    )


def batch_result(
    *,
    symbol: str,
    asset_id: UUID,
    bars: tuple[PriceBar, ...],
    retrieved_at: datetime,
) -> MarketBarBatchResult:
    return cast(
        MarketBarBatchResult,
        SimpleNamespace(
            results=(
                SimpleNamespace(
                    symbol=symbol,
                    asset_id=asset_id,
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


@pytest.fixture
def sessions() -> tuple[date, ...]:
    return (
        date(2025, 12, 30),
        date(2025, 12, 31),
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
        date(2026, 1, 9),
    )


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(
        email="daily-performance@example.com",
        password="test-password-123",
    )


@pytest.fixture
def asset() -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )


@pytest.fixture
def portfolio(
    owner: User,
    asset: Asset,
) -> Portfolio:
    return Portfolio.objects.create(
        user=owner,
        name="Daily Performance",
        benchmark_asset=asset,
    )


@pytest.mark.django_db
def test_daily_series_uses_adjusted_close_and_external_flow_formula(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    first_as_of = datetime(2026, 1, 6, 23, tzinfo=UTC)
    second_as_of = datetime(2026, 1, 7, 23, tzinfo=UTC)
    third_as_of = datetime(2026, 1, 8, 23, tzinfo=UTC)
    retrieved_at = datetime(2026, 1, 8, 23, 30, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 1, 5, 12, tzinfo=UTC),
        source_sequence=1,
        cash_amount=Decimal("1000"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2026, 1, 5, 13, tzinfo=UTC),
        source_sequence=1,
        quantity=Decimal("10"),
        price=Decimal("50"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 1, 7, 12, tzinfo=UTC),
        source_sequence=1,
        cash_amount=Decimal("200"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.WITHDRAWAL,
        occurred_at=datetime(2026, 1, 8, 12, tzinfo=UTC),
        source_sequence=1,
        cash_amount=Decimal("100"),
    )

    bars = (
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 6),
            raw_close=500.0,
            adjusted_close=50.0,
            retrieved_at=retrieved_at,
        ),
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 7),
            raw_close=550.0,
            adjusted_close=55.0,
            retrieved_at=retrieved_at,
        ),
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 8),
            raw_close=600.0,
            adjusted_close=60.0,
            retrieved_at=retrieved_at,
        ),
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 9),
            raw_close=9999.0,
            adjusted_close=9999.0,
            retrieved_at=retrieved_at,
        ),
    )

    def executor(
        *args: object,
        **kwargs: object,
    ) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            asset_id=asset.id,
            bars=bars,
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = calculate_owned_portfolio_daily_performance(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        valuation_times=(
            first_as_of,
            second_as_of,
            third_as_of,
        ),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(
            MarketBarQueryExecutor,
            executor,
        ),
    )

    assert tuple(valuation.total_value for valuation in result.valuations) == (
        Decimal("1000.0"),
        Decimal("1250.0"),
        Decimal("1200.0"),
    )
    assert tuple(valuation.net_external_flow for valuation in result.valuations) == (
        Decimal("0"),
        Decimal("200"),
        Decimal("-100"),
    )

    assert result.twr is not None
    assert tuple(item.simple_return for item in result.twr.daily_returns) == pytest.approx(
        (0.05, 0.04)
    )
    assert result.twr.cumulative_return == pytest.approx(0.092)

    assert result.provenance.provider == "mock"
    assert result.provenance.price_field == "adjusted_close"
    assert result.provenance.benchmark_asset_id == asset.id


@pytest.mark.django_db
def test_future_bar_cannot_change_prior_daily_valuation(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    first_as_of = datetime(2026, 1, 6, 23, tzinfo=UTC)
    second_as_of = datetime(2026, 1, 7, 23, tzinfo=UTC)
    retrieved_at = datetime(2026, 1, 9, 23, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 1, 5, 12, tzinfo=UTC),
        cash_amount=Decimal("100"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2026, 1, 5, 13, tzinfo=UTC),
        quantity=Decimal("1"),
        price=Decimal("50"),
    )

    bars = (
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 6),
            raw_close=50.0,
            adjusted_close=50.0,
            retrieved_at=retrieved_at,
        ),
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 7),
            raw_close=55.0,
            adjusted_close=55.0,
            retrieved_at=retrieved_at,
        ),
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 9),
            raw_close=1000.0,
            adjusted_close=1000.0,
            retrieved_at=retrieved_at,
        ),
    )

    def executor(
        *args: object,
        **kwargs: object,
    ) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            asset_id=asset.id,
            bars=bars,
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = calculate_owned_portfolio_daily_performance(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        valuation_times=(
            first_as_of,
            second_as_of,
        ),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(
            MarketBarQueryExecutor,
            executor,
        ),
    )

    assert result.valuations[0].positions[0].adjusted_close == Decimal("50.0")
    assert result.valuations[1].positions[0].adjusted_close == Decimal("55.0")


@pytest.mark.django_db
def test_too_stale_price_makes_series_and_twr_incomplete(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    first_as_of = datetime(2026, 1, 7, 23, tzinfo=UTC)
    second_as_of = datetime(2026, 1, 8, 23, tzinfo=UTC)
    retrieved_at = datetime(2026, 1, 8, 23, 30, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2025, 12, 31, 12, tzinfo=UTC),
        quantity=Decimal("1"),
        price=Decimal("50"),
    )

    bars = (
        price_bar(
            asset_id=asset.id,
            trade_date=date(2026, 1, 2),
            raw_close=50.0,
            adjusted_close=50.0,
            retrieved_at=retrieved_at,
        ),
    )

    def executor(
        *args: object,
        **kwargs: object,
    ) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            asset_id=asset.id,
            bars=bars,
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = calculate_owned_portfolio_daily_performance(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        valuation_times=(
            first_as_of,
            second_as_of,
        ),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(
            MarketBarQueryExecutor,
            executor,
        ),
    )

    assert result.twr is None
    assert any(
        warning.code is DailyPerformanceWarningCode.PRICE_TOO_STALE for warning in result.warnings
    )
    assert any(
        warning.code is DailyPerformanceWarningCode.TWR_UNDEFINED for warning in result.warnings
    )
