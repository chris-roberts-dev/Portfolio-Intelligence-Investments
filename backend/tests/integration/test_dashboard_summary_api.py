"""API coverage for the authenticated P0 portfolio summary endpoint."""

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
from apps.portfolios.api import summary_views
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)
from apps.portfolios.services.dashboard_summary import (
    DashboardPortfolioSummaryMetrics,
    DashboardPortfolioSummaryProvenance,
    DashboardPortfolioSummaryResult,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001101")
FIXED_NOW = datetime(2026, 9, 15, 16, tzinfo=UTC)


def summary_result() -> DashboardPortfolioSummaryResult:
    return DashboardPortfolioSummaryResult(
        metrics=DashboardPortfolioSummaryMetrics(
            total_market_value=Decimal("1250.50"),
            total_market_value_unavailable_reason=None,
            net_contributions=Decimal("1000.00"),
            cost_basis=Decimal("900.00"),
            cash_balance=Decimal("250.50"),
            cash_percentage=Decimal("0.2003198720511795281887245102"),
            cash_percentage_unavailable_reason=None,
            unrealized_gain_loss=Decimal("100.00"),
            unrealized_gain_loss_unavailable_reason=None,
            selected_period_realized_gain_loss=Decimal("25.00"),
            selected_period_realized_gain_loss_unavailable_reason=None,
            selected_period_income_received=Decimal("12.50"),
            selected_period_income_unavailable_reason=None,
        ),
        data_quality=PerformanceDataQualityState.CURRENT,
        warnings=(),
        provenance=DashboardPortfolioSummaryProvenance(
            portfolio_id=PORTFOLIO_ID,
            base_currency="USD",
            provider="mock",
            requested_start=date(2026, 9, 1),
            requested_end_exclusive=date(2026, 9, 16),
            ledger_as_of=FIXED_NOW,
            current_price_data_as_of=FIXED_NOW,
            calculated_at=FIXED_NOW,
            current_price_field="close",
            accounting_method="WEIGHTED_AVERAGE_BOOK_COST_V1",
            accounting_assumptions=("Weighted-average analytical book cost.",),
            selected_period_transaction_timezone="UTC",
            net_contributions_scope="LIFETIME_THROUGH_LEDGER_AS_OF",
            selected_period_accounting_scope=("REQUESTED_RANGE_INTERSECTED_WITH_LEDGER_AS_OF"),
        ),
    )


@pytest.mark.django_db
def test_summary_endpoint_is_owner_scoped_and_preserves_decimal_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="summary-api@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=owner,
        name="Summary API",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        summary_views,
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
        summary_views,
        "get_asset_resolver",
        lambda: object(),
    )
    monkeypatch.setattr(
        summary_views,
        "get_trading_session_calendar",
        lambda: object(),
    )
    monkeypatch.setattr(
        summary_views,
        "get_current_time",
        lambda: FIXED_NOW,
    )

    def fake_build(**kwargs: object) -> DashboardPortfolioSummaryResult:
        captured.update(kwargs)
        return summary_result()

    monkeypatch.setattr(
        summary_views,
        "build_owned_portfolio_dashboard_summary",
        fake_build,
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-summary",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-16",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["metrics"]["total_market_value"] == "1250.50"
    assert response.data["metrics"]["net_contributions"] == "1000.00"
    assert response.data["metrics"]["cost_basis"] == "900.00"
    assert response.data["metrics"]["cash_balance"] == "250.50"
    assert response.data["metrics"]["unrealized_gain_loss"] == "100.00"
    assert response.data["metrics"]["selected_period_realized_gain_loss"] == "25.00"
    assert response.data["metrics"]["selected_period_income_received"] == "12.50"
    assert response.data["provenance"]["accounting_method"] == ("WEIGHTED_AVERAGE_BOOK_COST_V1")
    assert captured["user"] == owner
    assert captured["portfolio_id"] == portfolio.id


@pytest.mark.django_db
def test_summary_endpoint_hides_another_users_portfolio() -> None:
    owner = User.objects.create_user(
        email="summary-owner@example.com",
        password="test-password-123",
    )
    other = User.objects.create_user(
        email="summary-other@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=other,
        name="Other Portfolio",
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-summary",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-16",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "PORTFOLIO_NOT_FOUND"
