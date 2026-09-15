"""API coverage for the authenticated P0 allocation endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.portfolios.api import allocation_views
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_allocation import (
    DashboardAllocationGroup,
    DashboardAllocationProvenance,
    DashboardAllocationResult,
    DashboardAllocationTotals,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001301")
FIXED_NOW = datetime(2026, 9, 15, 21, tzinfo=UTC)


def allocation_result() -> DashboardAllocationResult:
    return DashboardAllocationResult(
        allocation_available=True,
        groups=(
            DashboardAllocationGroup(
                key="STOCK",
                label="Stocks",
                is_cash=False,
                asset_count=2,
                market_value=Decimal("600.00"),
                weight=0.6,
            ),
            DashboardAllocationGroup(
                key="ETF",
                label="ETFs",
                is_cash=False,
                asset_count=1,
                market_value=Decimal("300.00"),
                weight=0.3,
            ),
            DashboardAllocationGroup(
                key="CASH",
                label="Cash",
                is_cash=True,
                asset_count=0,
                market_value=Decimal("100.00"),
                weight=0.1,
            ),
        ),
        totals=DashboardAllocationTotals(
            total_market_value=Decimal("1000.00"),
            invested_value=Decimal("900.00"),
            cash_value=Decimal("100.00"),
            invested_weight=0.9,
            cash_weight=0.1,
        ),
        data_quality=PerformanceDataQualityState.CURRENT,
        unavailable_reason=None,
        warnings=(),
        provenance=DashboardAllocationProvenance(
            portfolio_id=PORTFOLIO_ID,
            base_currency="USD",
            provider="mock",
            as_of=FIXED_NOW,
            data_as_of=FIXED_NOW,
            calculated_at=FIXED_NOW,
            price_field="close",
            grouping_dimension="ASSET_CLASS",
            supported_grouping_dimensions=("ASSET_CLASS",),
            grouping_source="Asset.asset_type",
            ordering_rule=("SECURITY_WEIGHT_DESC_THEN_GROUP_KEY_CASH_LAST_V1"),
            other_grouping_applied=False,
            other_grouping_threshold=None,
            other_grouping_rule=(
                "No Other aggregation is applied in the MVP because "
                "persisted security asset types are exhaustively "
                "constrained to STOCK and ETF."
            ),
            weight_sum_tolerance=1e-8,
        ),
    )


@pytest.mark.django_db
def test_allocation_endpoint_is_owner_scoped_and_preserves_exact_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="allocation-api@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=owner,
        name="Allocation API",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        allocation_views,
        "_provider_context_for_request",
        lambda *_args, **_kwargs: SimpleNamespace(
            name="mock",
            provider=MockMarketDataProvider(
                {},
                retrieved_at=FIXED_NOW,
            ),
        ),
    )
    monkeypatch.setattr(
        allocation_views,
        "get_asset_resolver",
        lambda: object(),
    )
    monkeypatch.setattr(
        allocation_views,
        "get_trading_session_calendar",
        lambda: object(),
    )
    monkeypatch.setattr(
        allocation_views,
        "get_current_time",
        lambda: FIXED_NOW,
    )

    def fake_build(**kwargs: object) -> DashboardAllocationResult:
        captured.update(kwargs)
        return allocation_result()

    monkeypatch.setattr(
        allocation_views,
        "build_owned_portfolio_dashboard_allocation",
        fake_build,
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-allocation",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["allocation_available"] is True

    assert response.data["groups"][0]["key"] == "STOCK"
    assert response.data["groups"][0]["market_value"] == "600.00"
    assert response.data["groups"][0]["weight"] == pytest.approx(0.6)

    assert response.data["groups"][-1]["key"] == "CASH"
    assert response.data["groups"][-1]["market_value"] == "100.00"

    assert response.data["totals"]["total_market_value"] == "1000.00"
    assert response.data["totals"]["invested_value"] == "900.00"
    assert response.data["totals"]["cash_value"] == "100.00"

    assert response.data["provenance"]["grouping_dimension"] == "ASSET_CLASS"
    assert response.data["provenance"]["supported_grouping_dimensions"] == ["ASSET_CLASS"]
    assert response.data["provenance"]["other_grouping_applied"] is False

    assert captured["user"] == owner
    assert captured["portfolio_id"] == portfolio.id


@pytest.mark.django_db
def test_allocation_endpoint_hides_another_users_portfolio() -> None:
    owner = User.objects.create_user(
        email="allocation-owner@example.com",
        password="test-password-123",
    )
    other = User.objects.create_user(
        email="allocation-other@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=other,
        name="Other Allocation",
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-allocation",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "PORTFOLIO_NOT_FOUND"
