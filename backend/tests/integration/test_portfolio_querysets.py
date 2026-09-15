"""Integration tests for typed portfolio and transaction QuerySet scoping."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.portfolios.models import Portfolio, Transaction, TransactionType


@pytest.mark.django_db
def test_portfolio_manager_scopes_to_owner() -> None:
    owner = User.objects.create_user(
        email="owner@example.com",
        password="test-password-123",
    )
    other_user = User.objects.create_user(
        email="other@example.com",
        password="test-password-123",
    )
    owned = Portfolio.objects.create(
        user=owner,
        name="Owned",
    )
    Portfolio.objects.create(
        user=other_user,
        name="Not Owned",
    )

    assert list(
        Portfolio.objects.owned_by(owner).values_list(
            "id",
            flat=True,
        )
    ) == [owned.id]


@pytest.mark.django_db
def test_transaction_manager_scopes_by_owner_and_portfolio() -> None:
    owner = User.objects.create_user(
        email="owner-transactions@example.com",
        password="test-password-123",
    )
    other_user = User.objects.create_user(
        email="other-transactions@example.com",
        password="test-password-123",
    )
    owned_portfolio = Portfolio.objects.create(
        user=owner,
        name="Owned",
    )
    other_portfolio = Portfolio.objects.create(
        user=other_user,
        name="Other",
    )
    occurred_at = datetime(2026, 1, 2, 12, tzinfo=UTC)
    owned_transaction = Transaction.objects.create(
        portfolio=owned_portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        cash_amount=Decimal("100"),
    )
    Transaction.objects.create(
        portfolio=other_portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        cash_amount=Decimal("200"),
    )

    assert list(
        Transaction.objects.owned_by(owner).values_list(
            "id",
            flat=True,
        )
    ) == [owned_transaction.id]
    assert list(
        Transaction.objects.for_portfolio(owned_portfolio).values_list(
            "id",
            flat=True,
        )
    ) == [owned_transaction.id]


@pytest.mark.django_db
def test_transaction_replay_scope_is_inclusive_and_deterministic() -> None:
    owner = User.objects.create_user(
        email="ordered-transactions@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Ordered",
    )
    occurred_at = datetime(2026, 1, 2, 12, tzinfo=UTC)

    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        source_sequence=2,
        cash_amount=Decimal("200"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        source_sequence=1,
        cash_amount=Decimal("100"),
    )
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at + timedelta(days=1),
        source_sequence=1,
        cash_amount=Decimal("300"),
    )

    sequences = list(
        Transaction.objects.for_portfolio(portfolio)
        .through(occurred_at)
        .ordered_for_replay()
        .values_list(
            "source_sequence",
            flat=True,
        )
    )

    assert sequences == [1, 2]


def test_transaction_through_rejects_naive_as_of() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Transaction.objects.through(datetime(2026, 1, 2, 12))
