"""Integration tests for canonical manual transaction writes and asset catalog."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.portfolios.models import Portfolio, Transaction
from apps.portfolios.services.ledger import replay_portfolio_ledger


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(
        email="transaction-owner@example.com",
        password="test-password-123",
    )


@pytest.fixture
def other_user() -> User:
    return User.objects.create_user(
        email="transaction-other@example.com",
        password="test-password-123",
    )


@pytest.fixture
def portfolio(owner: User) -> Portfolio:
    return Portfolio.objects.create(
        user=owner,
        name="Transaction Portfolio",
    )


@pytest.fixture
def asset() -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )


@pytest.mark.django_db
def test_asset_catalog_returns_only_active_canonical_usd_assets(
    owner: User,
) -> None:
    active = Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
    )
    Asset.objects.create(
        symbol="MSFT",
        name="Microsoft Corp.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        is_active=False,
    )

    response = authenticated_client(owner).get(reverse("api-v1-asset-catalog"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == [
        {
            "id": str(active.id),
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "asset_type": "STOCK",
            "exchange": "NASDAQ",
            "currency": "USD",
        }
    ]


@pytest.mark.django_db
def test_manual_transactions_replay_through_authoritative_ledger(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    client = authenticated_client(owner)
    occurred_at = datetime(2026, 9, 15, 14, tzinfo=UTC)

    deposit = client.post(
        reverse(
            "api-v1-portfolio-transaction-create",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "transaction_type": "DEPOSIT",
            "occurred_at": occurred_at.isoformat(),
            "cash_amount": "1000.00",
        },
        format="json",
    )
    buy = client.post(
        reverse(
            "api-v1-portfolio-transaction-create",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "transaction_type": "BUY",
            "occurred_at": occurred_at.isoformat(),
            "asset_id": str(asset.id),
            "quantity": "2",
            "price": "100",
            "fees": "1",
        },
        format="json",
    )

    assert deposit.status_code == status.HTTP_201_CREATED
    assert buy.status_code == status.HTTP_201_CREATED
    assert deposit.data["source_sequence"] == 0
    assert buy.data["source_sequence"] == 1
    assert buy.data["cash_amount"] is None

    replay = replay_portfolio_ledger(portfolio)
    assert replay.cash_balance == Decimal("799")
    assert replay.transaction_count == 2
    assert replay.positions[0].asset_id == asset.id
    assert replay.positions[0].quantity == Decimal("2")


@pytest.mark.django_db
def test_manual_transaction_rejects_invalid_field_combination(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-create",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "transaction_type": "DEPOSIT",
            "occurred_at": "2026-09-15T14:00:00Z",
            "asset_id": str(asset.id),
            "cash_amount": "100.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "INVALID_TRANSACTION"
    assert "asset_id" in response.data["errors"]
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_manual_transaction_rejects_unknown_canonical_asset(
    owner: User,
    portfolio: Portfolio,
) -> None:
    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-create",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "transaction_type": "BUY",
            "occurred_at": "2026-09-15T14:00:00Z",
            "asset_id": "00000000-0000-0000-0000-000000000099",
            "quantity": "1",
            "price": "100",
            "fees": "0",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "ASSET_NOT_FOUND"
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_manual_sell_that_would_create_negative_position_is_rolled_back(
    owner: User,
    portfolio: Portfolio,
    asset: Asset,
) -> None:
    response = authenticated_client(owner).post(
        reverse(
            "api-v1-portfolio-transaction-create",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "transaction_type": "SELL",
            "occurred_at": "2026-09-15T14:00:00Z",
            "asset_id": str(asset.id),
            "quantity": "1",
            "price": "100",
            "fees": "0",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "NEGATIVE_POSITION"
    assert Transaction.objects.count() == 0


@pytest.mark.django_db
def test_user_cannot_write_transaction_to_another_users_portfolio(
    other_user: User,
    portfolio: Portfolio,
) -> None:
    response = authenticated_client(other_user).post(
        reverse(
            "api-v1-portfolio-transaction-create",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "transaction_type": "DEPOSIT",
            "occurred_at": "2026-09-15T14:00:00Z",
            "cash_amount": "100.00",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Transaction.objects.count() == 0
