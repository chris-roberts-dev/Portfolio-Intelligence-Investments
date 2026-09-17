from __future__ import annotations

from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.portfolios.models import Portfolio
from apps.rebalancing.models import TargetAllocation


@pytest.mark.django_db
def test_owner_can_create_target_allocation_with_cash() -> None:
    user = User.objects.create_user(email="owner@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Owned")
    asset = Asset.objects.create(
        id=UUID("00000000-0000-0000-0000-000000000101"),
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse("api-v1-target-allocation-list"),
        {
            "portfolio_id": str(portfolio.id),
            "name": "60/40 target",
            "weights": [
                {"asset_id": str(asset.id), "weight": 0.6},
                {"asset_id": None, "weight": 0.4},
            ],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["portfolio_id"] == str(portfolio.id)
    assert len(response.data["weights"]) == 2


@pytest.mark.django_db
def test_target_allocation_creation_does_not_cross_user_portfolio_boundary() -> None:
    owner = User.objects.create_user(email="owner@example.com", password="password")
    other = User.objects.create_user(email="other@example.com", password="password")
    portfolio = Portfolio.objects.create(user=owner, name="Owned")
    client = APIClient()
    client.force_authenticate(user=other)
    response = client.post(
        reverse("api-v1-target-allocation-list"),
        {
            "portfolio_id": str(portfolio.id),
            "name": "Unauthorized",
            "weights": [{"asset_id": None, "weight": 1.0}],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert not TargetAllocation.objects.filter(user=other).exists()
