from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.services.asset_discovery import (
    CanonicalAssetResolutionBatch,
    CanonicalAssetResolutionOutcome,
    CanonicalAssetResolutionStatus,
)

AAPL_ID = UUID("00000000-0000-0000-0000-000000000011")


@pytest.mark.django_db
def test_authenticated_asset_resolve_returns_canonical_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(email="resolve@example.com", password="password")
    Asset.objects.create(
        id=AAPL_ID,
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        currency="USD",
        is_active=True,
    )

    monkeypatch.setattr(
        "apps.portfolios.api.management_views.load_market_data_provider_configuration",
        lambda: SimpleNamespace(default_provider="yfinance"),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.resolve_canonical_assets_with_discovery",
        lambda *args, **kwargs: CanonicalAssetResolutionBatch(
            provider="yfinance",
            outcomes=(
                CanonicalAssetResolutionOutcome(
                    symbol="AAPL",
                    status=CanonicalAssetResolutionStatus.RESOLVED,
                    asset_id=AAPL_ID,
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.get_asset_resolver",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.get_asset_discovery_provider",
        lambda _provider_name: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "apps.portfolios.api.management_views.get_asset_catalog_writer",
        lambda: SimpleNamespace(),
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse("api-v1-asset-resolve"),
        {"symbols": ["aapl"]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["provider"] == "yfinance"
    assert response.data["outcomes"] == [
        {
            "symbol": "AAPL",
            "status": "RESOLVED",
            "asset": {
                "id": str(AAPL_ID),
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "STOCK",
                "exchange": "NASDAQ",
                "currency": "USD",
            },
            "warning": None,
        }
    ]


@pytest.mark.django_db
def test_asset_resolve_requires_authentication() -> None:
    response = APIClient().post(
        reverse("api-v1-asset-resolve"),
        {"symbols": ["AAPL"]},
        format="json",
    )
    assert response.status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }
