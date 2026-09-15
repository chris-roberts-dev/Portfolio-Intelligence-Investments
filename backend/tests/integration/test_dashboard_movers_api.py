"""API coverage for authenticated dashboard mover rankings."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.services.asset_resolution import InMemoryAssetResolver
from apps.portfolios.api import movers_views
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_movers import (
    DashboardMover,
    DashboardMoversProvenance,
    DashboardMoversResult,
    MoversAttributionStatus,
    MoversReconciliation,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000000801")
ASSET_ID = UUID("00000000-0000-0000-0000-000000000811")
FIXED_NOW = datetime(2026, 1, 6, 23, tzinfo=UTC)


class FixedCalendar:
    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        del count
        return tuple(
            session
            for session in (
                date(2026, 1, 2),
                date(2026, 1, 5),
                date(2026, 1, 6),
            )
            if session <= as_of_date
        )


def mover() -> DashboardMover:
    return DashboardMover(
        asset_id=ASSET_ID,
        symbol="AAA",
        name="AAA Security",
        asset_type="STOCK",
        currency="USD",
        is_current_holding=True,
        quantity=Decimal("2"),
        current_price=Decimal("55.00"),
        current_price_date=date(2026, 1, 6),
        current_price_retrieved_at=FIXED_NOW,
        stale_trading_sessions=0,
        market_value=Decimal("110.00"),
        weight=0.55,
        selected_period_return=0.10,
        contribution_to_return=0.06,
        sparkline=(),
        data_quality=PerformanceDataQualityState.CURRENT,
        unavailable_reasons=(),
    )


def result() -> DashboardMoversResult:
    item = mover()
    return DashboardMoversResult(
        top_gainers=(item,),
        top_losers=(),
        largest_contributors=(item,),
        largest_detractors=(),
        reconciliation=MoversReconciliation(
            status=MoversAttributionStatus.AVAILABLE,
            periods=2,
            cumulative_return=0.08,
            asset_contribution_total=0.08,
            unattributed_contribution=0.0,
            reconciliation_error=0.0,
            unavailable_reason=None,
        ),
        data_quality=PerformanceDataQualityState.CURRENT,
        warnings=(),
        provenance=DashboardMoversProvenance(
            portfolio_id=PORTFOLIO_ID,
            base_currency="USD",
            provider="mock",
            requested_start=date(2026, 1, 2),
            requested_end_exclusive=date(2026, 1, 7),
            effective_start=date(2026, 1, 2),
            effective_end_exclusive=date(2026, 1, 7),
            current_price_as_of=FIXED_NOW,
            period_data_as_of=FIXED_NOW,
            calculated_at=FIXED_NOW,
            current_price_field="close",
            period_price_field="adjusted_close",
            attribution_method="ASSET_PNL_WEALTH_LINKED_V1",
            engine_version="0.1.0.dev0",
        ),
    )


@pytest.mark.django_db
def test_movers_endpoint_is_owner_scoped_and_passes_server_side_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="movers-api@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=owner,
        name="Movers API",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        movers_views,
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
        movers_views,
        "get_asset_resolver",
        lambda: InMemoryAssetResolver(()),
    )
    monkeypatch.setattr(
        movers_views,
        "get_trading_session_calendar",
        FixedCalendar,
    )
    monkeypatch.setattr(
        movers_views,
        "get_current_time",
        lambda: FIXED_NOW,
    )

    def fake_build(**kwargs: object) -> DashboardMoversResult:
        captured.update(kwargs)
        return result()

    monkeypatch.setattr(
        movers_views,
        "build_owned_portfolio_dashboard_movers",
        fake_build,
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-movers",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-01-01",
            "end": "2026-01-07",
            "limit": "7",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["top_gainers"][0]["symbol"] == "AAA"
    assert response.data["largest_contributors"][0]["contribution_to_return"] == pytest.approx(0.06)
    assert response.data["reconciliation"]["unattributed_contribution"] == pytest.approx(0.0)
    assert captured["user"] == owner
    assert captured["portfolio_id"] == portfolio.id
    assert captured["limit"] == 7


@pytest.mark.django_db
def test_movers_endpoint_rejects_out_of_range_limit() -> None:
    owner = User.objects.create_user(
        email="movers-limit@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Mover Limit",
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-movers",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-01-01",
            "end": "2026-01-07",
            "limit": "21",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "limit" in response.data["errors"]
