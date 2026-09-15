"""Integration tests for deterministic portfolio-ledger replay."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.ledger import (
    CashFlowClassification,
    NegativePositionError,
    replay_portfolio_ledger,
)


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(
        email="ledger-owner@example.com",
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
def portfolio(owner: User) -> Portfolio:
    return Portfolio.objects.create(
        user=owner,
        name="Ledger Portfolio",
    )


@pytest.mark.django_db
def test_replay_derives_quantities_cash_and_cash_flow_classification(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    start = datetime(2026, 1, 2, 12, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=start,
        source_sequence=1,
        cash_amount=Decimal("1000"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=start + timedelta(days=1),
        source_sequence=1,
        quantity=Decimal("2"),
        price=Decimal("100"),
        fees=Decimal("1"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DIVIDEND,
        asset=asset,
        occurred_at=start + timedelta(days=2),
        source_sequence=1,
        cash_amount=Decimal("5"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.SELL,
        asset=asset,
        occurred_at=start + timedelta(days=3),
        source_sequence=1,
        quantity=Decimal("1"),
        price=Decimal("120"),
        fees=Decimal("2"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.WITHDRAWAL,
        occurred_at=start + timedelta(days=4),
        source_sequence=1,
        cash_amount=Decimal("22"),
    )

    result = replay_portfolio_ledger(portfolio)

    assert result.cash_balance == Decimal("900")
    assert result.net_external_cash_flow == Decimal("978")
    assert result.net_internal_cash_flow == Decimal("-78")
    assert result.transaction_count == 5

    assert len(result.positions) == 1
    assert result.positions[0].asset_id == asset.id
    assert result.positions[0].quantity == Decimal("1")

    assert tuple(cash_flow.classification for cash_flow in result.cash_flows) == (
        CashFlowClassification.EXTERNAL,
        CashFlowClassification.INTERNAL,
        CashFlowClassification.INTERNAL,
        CashFlowClassification.INTERNAL,
        CashFlowClassification.EXTERNAL,
    )
    assert tuple(cash_flow.amount for cash_flow in result.cash_flows) == (
        Decimal("1000"),
        Decimal("-201"),
        Decimal("5"),
        Decimal("118"),
        Decimal("-22"),
    )

    assert isinstance(result.cash_balance, Decimal)
    assert all(isinstance(position.quantity, Decimal) for position in result.positions)


@pytest.mark.django_db
def test_replay_through_as_of_is_inclusive(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    deposit_time = datetime(2026, 1, 2, 12, tzinfo=UTC)
    buy_time = deposit_time + timedelta(days=1)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=deposit_time,
        cash_amount=Decimal("1000"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=buy_time,
        quantity=Decimal("1"),
        price=Decimal("100"),
    )

    result = replay_portfolio_ledger(
        portfolio,
        as_of=deposit_time,
    )

    assert result.as_of == deposit_time
    assert result.cash_balance == Decimal("1000")
    assert result.positions == ()
    assert result.transaction_count == 1


@pytest.mark.django_db
def test_replay_rejects_sell_that_would_create_negative_position(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    occurred_at = datetime(2026, 1, 2, 12, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=occurred_at,
        source_sequence=1,
        quantity=Decimal("1"),
        price=Decimal("100"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.SELL,
        asset=asset,
        occurred_at=occurred_at,
        source_sequence=2,
        quantity=Decimal("2"),
        price=Decimal("100"),
    )

    with pytest.raises(
        NegativePositionError,
        match="negative position",
    ):
        replay_portfolio_ledger(portfolio)


@pytest.mark.django_db
def test_replay_uses_source_sequence_not_insertion_order(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    occurred_at = datetime(2026, 1, 2, 12, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.SELL,
        asset=asset,
        occurred_at=occurred_at,
        source_sequence=2,
        quantity=Decimal("1"),
        price=Decimal("110"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=occurred_at,
        source_sequence=1,
        quantity=Decimal("1"),
        price=Decimal("100"),
    )

    result = replay_portfolio_ledger(portfolio)

    assert result.positions == ()
    assert result.cash_balance == Decimal("10")
    assert tuple(cash_flow.source_sequence for cash_flow in result.cash_flows) == (1, 2)


@pytest.mark.django_db
def test_replay_positions_are_stably_ordered_by_asset_id(
    portfolio: Portfolio,
) -> None:
    first_asset = Asset.objects.create(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        symbol="MSFT",
        name="Microsoft Corp.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )
    second_asset = Asset.objects.create(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )
    occurred_at = datetime(2026, 1, 2, 12, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=first_asset,
        occurred_at=occurred_at,
        source_sequence=1,
        quantity=Decimal("1"),
        price=Decimal("100"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=second_asset,
        occurred_at=occurred_at,
        source_sequence=2,
        quantity=Decimal("2"),
        price=Decimal("100"),
    )

    result = replay_portfolio_ledger(portfolio)

    assert tuple(position.asset_id for position in result.positions) == (
        second_asset.id,
        first_asset.id,
    )
