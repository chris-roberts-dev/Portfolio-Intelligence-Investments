"""Integration tests for owned-portfolio current valuation."""

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
    CurrentValuationWarningCode,
    MarketBarQueryExecutor,
    value_owned_portfolio,
)
from portfolio_engine.contracts.market_data import PriceBar


class FixedTradingCalendar:
    """Deterministic trading-session calendar for valuation tests."""

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


def bar(
    *,
    asset_id: UUID,
    trade_date: date,
    close: float,
    retrieved_at: datetime,
) -> PriceBar:
    return PriceBar(
        asset_id=asset_id,
        trade_date=trade_date,
        open=close,
        high=close,
        low=close,
        close=close,
        adjusted_close=close,
        volume=1000,
        source="mock",
        retrieved_at=retrieved_at,
    )


def batch_result(
    *,
    symbol: str,
    status: MarketBarStatus,
    bars: tuple[PriceBar, ...],
    retrieved_at: datetime,
) -> MarketBarBatchResult:
    return cast(
        MarketBarBatchResult,
        SimpleNamespace(
            results=(
                SimpleNamespace(
                    symbol=symbol,
                    status=status,
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
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
    )


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(
        email="valuation-owner@example.com",
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
        name="Valuation Portfolio",
        benchmark_asset=asset,
    )


def dependencies() -> tuple[
    AssetResolver,
    MarketDataProvider,
]:
    return (
        cast(AssetResolver, object()),
        cast(MarketDataProvider, object()),
    )


@pytest.mark.django_db
def test_owned_portfolio_uses_ledger_raw_close_and_existing_engine_helpers(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    occurred_at = datetime(2026, 1, 2, 12, tzinfo=UTC)
    retrieved_at = datetime(2026, 1, 8, 22, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        source_sequence=1,
        cash_amount=Decimal("1000"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=occurred_at,
        source_sequence=2,
        quantity=Decimal("2"),
        price=Decimal("100"),
    )

    def executor(*args: object, **kwargs: object) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            status=MarketBarStatus.SUCCEEDED,
            bars=(
                bar(
                    asset_id=asset.id,
                    trade_date=sessions[-1],
                    close=120.0,
                    retrieved_at=retrieved_at,
                ),
            ),
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = value_owned_portfolio(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        as_of=datetime(2026, 1, 8, 23, tzinfo=UTC),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert result.is_complete
    assert result.warnings == ()
    assert result.valuation is not None
    assert result.allocation is not None

    assert result.ledger.cash_balance == Decimal("800")
    assert result.prices[0].quantity == Decimal("2")
    assert result.prices[0].raw_close == Decimal("120.0")
    assert result.prices[0].stale_trading_sessions == 0

    assert result.valuation.security_market_value == pytest.approx(240.0)
    assert result.valuation.cash_value == pytest.approx(800.0)
    assert result.valuation.total_market_value == pytest.approx(1040.0)

    assert result.provenance.portfolio_id == portfolio.id
    assert result.provenance.benchmark_asset_id == asset.id
    assert result.provenance.provider == "mock"
    assert result.provenance.retrieved_at == retrieved_at
    assert result.provenance.price_field == "close"


@pytest.mark.django_db
def test_price_within_three_session_limit_is_accepted_with_warning(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
        quantity=Decimal("1"),
        price=Decimal("100"),
    )
    retrieved_at = datetime(2026, 1, 8, 22, tzinfo=UTC)

    def executor(*args: object, **kwargs: object) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            status=MarketBarStatus.SUCCEEDED,
            bars=(
                bar(
                    asset_id=asset.id,
                    trade_date=sessions[-4],
                    close=110.0,
                    retrieved_at=retrieved_at,
                ),
            ),
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = value_owned_portfolio(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        as_of=datetime(2026, 1, 8, 23, tzinfo=UTC),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert result.is_complete
    assert result.valuation is not None
    assert result.prices[0].stale_trading_sessions == 3
    assert result.warnings[0].code is CurrentValuationWarningCode.STALE_PRICE_USED


@pytest.mark.django_db
def test_price_older_than_three_sessions_makes_valuation_incomplete(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
        quantity=Decimal("1"),
        price=Decimal("100"),
    )
    retrieved_at = datetime(2026, 1, 8, 22, tzinfo=UTC)

    def executor(*args: object, **kwargs: object) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            status=MarketBarStatus.SUCCEEDED,
            bars=(
                bar(
                    asset_id=asset.id,
                    trade_date=sessions[0],
                    close=110.0,
                    retrieved_at=retrieved_at,
                ),
            ),
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = value_owned_portfolio(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        as_of=datetime(2026, 1, 8, 23, tzinfo=UTC),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert not result.is_complete
    assert result.valuation is None
    assert result.allocation is None
    assert result.prices == ()
    assert result.warnings[0].code is CurrentValuationWarningCode.PRICE_TOO_STALE


@pytest.mark.django_db
def test_no_data_makes_valuation_explicitly_incomplete(
    portfolio: Portfolio,
    asset: Asset,
    sessions: tuple[date, ...],
) -> None:
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
        quantity=Decimal("1"),
        price=Decimal("100"),
    )
    retrieved_at = datetime(2026, 1, 8, 22, tzinfo=UTC)

    def executor(*args: object, **kwargs: object) -> MarketBarBatchResult:
        return batch_result(
            symbol="AAPL",
            status=MarketBarStatus.NO_DATA,
            bars=(),
            retrieved_at=retrieved_at,
        )

    resolver, provider = dependencies()
    result = value_owned_portfolio(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        as_of=datetime(2026, 1, 8, 23, tzinfo=UTC),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(MarketBarQueryExecutor, executor),
    )

    assert not result.is_complete
    assert result.valuation is None
    assert result.allocation is None
    assert result.warnings[0].code is CurrentValuationWarningCode.PRICE_NO_DATA


@pytest.mark.django_db
def test_portfolio_ownership_scope_prevents_cross_user_valuation(
    portfolio: Portfolio,
    sessions: tuple[date, ...],
) -> None:
    other_user = User.objects.create_user(
        email="other-valuation-user@example.com",
        password="test-password-123",
    )
    resolver, provider = dependencies()

    with pytest.raises(Portfolio.DoesNotExist):
        value_owned_portfolio(
            user=other_user,
            portfolio_id=portfolio.id,
            as_of=datetime(2026, 1, 8, 23, tzinfo=UTC),
            provider_name="mock",
            resolver=resolver,
            provider=provider,
            trading_calendar=FixedTradingCalendar(sessions),
            executor=cast(
                MarketBarQueryExecutor,
                lambda *args, **kwargs: batch_result(
                    symbol="AAPL",
                    status=MarketBarStatus.NO_DATA,
                    bars=(),
                    retrieved_at=datetime(
                        2026,
                        1,
                        8,
                        22,
                        tzinfo=UTC,
                    ),
                ),
            ),
        )


@pytest.mark.django_db
def test_cash_only_portfolio_requires_no_market_data(
    portfolio: Portfolio,
    sessions: tuple[date, ...],
) -> None:
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 1, 2, 12, tzinfo=UTC),
        cash_amount=Decimal("500"),
    )

    def unexpected_executor(
        *args: object,
        **kwargs: object,
    ) -> MarketBarBatchResult:
        raise AssertionError("market data must not be requested")

    resolver, provider = dependencies()
    result = value_owned_portfolio(
        user=portfolio.user,
        portfolio_id=portfolio.id,
        as_of=datetime(2026, 1, 8, 23, tzinfo=UTC),
        provider_name="mock",
        resolver=resolver,
        provider=provider,
        trading_calendar=FixedTradingCalendar(sessions),
        executor=cast(
            MarketBarQueryExecutor,
            unexpected_executor,
        ),
    )

    assert result.is_complete
    assert result.prices == ()
    assert result.valuation is not None
    assert result.allocation is not None
    assert result.valuation.total_market_value == pytest.approx(500.0)
    assert result.allocation.cash_weight == pytest.approx(1.0)
    assert result.provenance.retrieved_at is None
