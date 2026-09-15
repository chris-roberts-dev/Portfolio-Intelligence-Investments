"""Focused tests for Phase 4 asset, portfolio, and transaction models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset, AssetProviderSymbol, AssetType
from apps.portfolios.models import Portfolio, Transaction, TransactionType


@pytest.fixture
def asset() -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )


@pytest.fixture
def portfolio(asset: Asset) -> Portfolio:
    user = User.objects.create_user(
        email="phase4-owner@example.com",
        password="test-password-123",
    )
    return Portfolio.objects.create(
        user=user,
        name="Primary Portfolio",
        benchmark_asset=asset,
    )


def test_transaction_type_set_matches_normative_ledger_contract() -> None:
    assert set(TransactionType.values) == {
        "DEPOSIT",
        "WITHDRAWAL",
        "BUY",
        "SELL",
        "DIVIDEND",
    }


@pytest.mark.django_db
def test_asset_uses_uuid_identity_and_usd_currency(asset: Asset) -> None:
    assert isinstance(asset.id, UUID)
    assert asset.currency == "USD"
    assert asset.asset_type == AssetType.STOCK
    assert timezone.is_aware(asset.created_at)
    assert timezone.is_aware(asset.updated_at)


@pytest.mark.django_db
def test_asset_database_rejects_non_usd_currency() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Asset.objects.create(
            symbol="VOD",
            name="Vodafone",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="EUR",
        )


@pytest.mark.django_db
def test_provider_symbol_identity_is_unique(asset: Asset) -> None:
    AssetProviderSymbol.objects.create(
        asset=asset,
        provider="yfinance",
        provider_symbol="AAPL",
        is_primary=True,
    )

    duplicate_asset = Asset.objects.create(
        symbol="AAPL-ALT",
        name="Alternate test asset",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        AssetProviderSymbol.objects.create(
            asset=duplicate_asset,
            provider="yfinance",
            provider_symbol="AAPL",
        )


@pytest.mark.django_db
def test_portfolio_links_user_benchmark_and_usd_base_currency(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    assert isinstance(portfolio.id, UUID)
    assert portfolio.base_currency == "USD"
    assert portfolio.benchmark_asset == asset
    assert timezone.is_aware(portfolio.created_at)
    assert timezone.is_aware(portfolio.updated_at)


@pytest.mark.django_db
def test_portfolio_database_rejects_non_usd_base_currency(asset: Asset) -> None:
    user = User.objects.create_user(
        email="non-usd-owner@example.com",
        password="test-password-123",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Portfolio.objects.create(
            user=user,
            name="EUR Portfolio",
            base_currency="EUR",
            benchmark_asset=asset,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "transaction_type,fields",
    [
        (
            TransactionType.DEPOSIT,
            {"cash_amount": Decimal("100.00")},
        ),
        (
            TransactionType.WITHDRAWAL,
            {"cash_amount": Decimal("25.00")},
        ),
        (
            TransactionType.BUY,
            {
                "quantity": Decimal("2.5"),
                "price": Decimal("100.25"),
                "fees": Decimal("1.50"),
            },
        ),
        (
            TransactionType.SELL,
            {
                "quantity": Decimal("1.25"),
                "price": Decimal("110.00"),
                "fees": Decimal("0.75"),
            },
        ),
        (
            TransactionType.DIVIDEND,
            {"cash_amount": Decimal("12.34")},
        ),
    ],
)
def test_supported_transaction_shapes_validate(
    portfolio: Portfolio,
    asset: Asset,
    transaction_type: TransactionType,
    fields: dict[str, Decimal],
) -> None:
    security_asset = (
        asset
        if transaction_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND)
        else None
    )
    ledger_entry = Transaction(
        portfolio=portfolio,
        transaction_type=transaction_type,
        asset=security_asset,
        occurred_at=timezone.now(),
        **fields,
    )

    ledger_entry.full_clean()


@pytest.mark.django_db
def test_buy_rejects_persisted_cash_amount(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Transaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset=asset,
            occurred_at=timezone.now(),
            quantity=Decimal("2"),
            price=Decimal("100"),
            fees=Decimal("1"),
            cash_amount=Decimal("201"),
        )


@pytest.mark.django_db
def test_deposit_rejects_security_fields(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    ledger_entry = Transaction(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        asset=asset,
        occurred_at=timezone.now(),
        cash_amount=Decimal("100"),
    )

    with pytest.raises(ValidationError):
        ledger_entry.full_clean()


@pytest.mark.django_db
def test_transaction_requires_timezone_aware_occurred_at(
    portfolio: Portfolio,
) -> None:
    ledger_entry = Transaction(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=datetime(2026, 1, 1, 12, 0, 0),
        cash_amount=Decimal("100"),
    )

    with pytest.raises(ValidationError, match="timezone-aware"):
        ledger_entry.full_clean()


@pytest.mark.django_db
def test_transaction_order_is_occurred_at_then_source_sequence(
    portfolio: Portfolio,
) -> None:
    occurred_at = timezone.now()
    later_sequence = Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        source_sequence=2,
        cash_amount=Decimal("200"),
    )
    earlier_sequence = Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        source_sequence=1,
        cash_amount=Decimal("100"),
    )

    ordered_ids = list(
        Transaction.objects.filter(portfolio=portfolio).values_list(
            "id",
            flat=True,
        )
    )

    assert ordered_ids == [earlier_sequence.id, later_sequence.id]


@pytest.mark.django_db
def test_transaction_ordering_key_is_unique_within_portfolio(
    portfolio: Portfolio,
) -> None:
    occurred_at = timezone.now()
    Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.DEPOSIT,
        occurred_at=occurred_at,
        source_sequence=7,
        cash_amount=Decimal("100"),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Transaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.DEPOSIT,
            occurred_at=occurred_at,
            source_sequence=7,
            cash_amount=Decimal("200"),
        )


@pytest.mark.django_db
def test_decimal_transaction_values_remain_decimal(
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    ledger_entry = Transaction.objects.create(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset=asset,
        occurred_at=timezone.now(),
        quantity=Decimal("1.250000000000"),
        price=Decimal("123.45678901"),
        fees=Decimal("0.01000000"),
    )
    ledger_entry.refresh_from_db()

    assert isinstance(ledger_entry.quantity, Decimal)
    assert isinstance(ledger_entry.price, Decimal)
    assert isinstance(ledger_entry.fees, Decimal)
    assert ledger_entry.quantity == Decimal("1.250000000000")
    assert ledger_entry.price == Decimal("123.45678901")
    assert ledger_entry.fees == Decimal("0.01000000")
