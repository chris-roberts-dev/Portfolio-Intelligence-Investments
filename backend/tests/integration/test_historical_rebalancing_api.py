from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.portfolios.models import Portfolio
from apps.rebalancing.models import HistoricalRebalanceComparison, TargetAllocation


@pytest.mark.django_db
def test_historical_comparison_api_is_owner_scoped_and_serializes_persisted_result() -> None:
    user = User.objects.create_user(email="owner@example.com", password="password")
    portfolio = Portfolio.objects.create(user=user, name="Owned")
    target = TargetAllocation.objects.create(user=user, portfolio=portfolio, name="Target")
    stored = HistoricalRebalanceComparison.objects.create(
        user=user,
        portfolio=portfolio,
        target_allocation=target,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        provider="mock",
        price_field="adjusted_close",
        drift_threshold="0.1",
        commission_rate="0",
        slippage_rate="0",
        engine_version="test",
        result={"policies": []},
        warnings=[],
    )
    other = User.objects.create_user(email="other@example.com", password="password")
    other_portfolio = Portfolio.objects.create(user=other, name="Other")
    other_target = TargetAllocation.objects.create(
        user=other, portfolio=other_portfolio, name="Other Target"
    )
    HistoricalRebalanceComparison.objects.create(
        user=other,
        portfolio=other_portfolio,
        target_allocation=other_target,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        provider="mock",
        price_field="adjusted_close",
        drift_threshold="0.1",
        commission_rate="0",
        slippage_rate="0",
        engine_version="test",
        result={"policies": []},
        warnings=[],
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("api-v1-historical-rebalance-comparison-list"))
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(stored.id)

    detail = client.get(reverse("api-v1-historical-rebalance-comparison-detail", args=[stored.id]))
    assert detail.status_code == status.HTTP_200_OK
    assert detail.data["price_field"] == "adjusted_close"
