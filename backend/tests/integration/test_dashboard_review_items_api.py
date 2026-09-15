"""API coverage for owner-scoped dashboard review items."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.portfolios.api import review_items_views
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_review_items import (
    DashboardReviewCount,
    DashboardReviewCounts,
    DashboardReviewDrilldown,
    DashboardReviewFilters,
    DashboardReviewItem,
    DashboardReviewItemsResult,
    DashboardReviewProvenance,
    ReviewDrilldownResource,
    ReviewItemCategory,
    ReviewItemSeverity,
    ReviewItemSource,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001501")
ASSET_ID = UUID("00000000-0000-0000-0000-000000001511")
FIXED_NOW = datetime(2026, 9, 15, 23, tzinfo=UTC)


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
                date(2026, 9, 1),
                date(2026, 9, 2),
                date(2026, 9, 15),
            )
            if session <= as_of_date
        )


def review_result() -> DashboardReviewItemsResult:
    item = DashboardReviewItem(
        key=(f"CURRENT_VALUATION:STALE_PRICE_USED:{ASSET_ID}:2026-09-15"),
        source=ReviewItemSource.CURRENT_VALUATION,
        severity=ReviewItemSeverity.WARNING,
        category=ReviewItemCategory.MARKET_DATA,
        code="STALE_PRICE_USED",
        message="Current price is one trading session stale.",
        drilldown=DashboardReviewDrilldown(
            resource=ReviewDrilldownResource.HOLDINGS,
            portfolio_id=PORTFOLIO_ID,
            requested_start=date(2026, 9, 1),
            requested_end_exclusive=date(2026, 9, 16),
            asset_id=ASSET_ID,
            symbol="AAPL",
            observation_date=date(2026, 9, 15),
        ),
    )

    return DashboardReviewItemsResult(
        counts=DashboardReviewCounts(
            total=1,
            by_severity=(
                DashboardReviewCount(key="ERROR", count=0),
                DashboardReviewCount(key="WARNING", count=1),
                DashboardReviewCount(key="INFO", count=0),
            ),
            by_category=(
                DashboardReviewCount(key="MARKET_DATA", count=1),
                DashboardReviewCount(key="DATA_COVERAGE", count=0),
                DashboardReviewCount(key="PROVIDER", count=0),
                DashboardReviewCount(key="VALUATION", count=0),
                DashboardReviewCount(key="ANALYTICS", count=0),
            ),
        ),
        filtered_count=1,
        filters=DashboardReviewFilters(
            severity=ReviewItemSeverity.WARNING,
            category=None,
        ),
        items=(item,),
        provenance=DashboardReviewProvenance(
            portfolio_id=PORTFOLIO_ID,
            base_currency="USD",
            provider="mock",
            requested_start=date(2026, 9, 1),
            requested_end_exclusive=date(2026, 9, 16),
            effective_start=date(2026, 9, 1),
            effective_end_exclusive=date(2026, 9, 16),
            current_data_as_of=FIXED_NOW,
            historical_data_as_of=FIXED_NOW,
            analytics_as_of_date=date(2026, 9, 15),
            calculated_at=FIXED_NOW,
            engine_version="0.1.0.dev0",
            included_sources=(
                ReviewItemSource.CURRENT_VALUATION,
                ReviewItemSource.DAILY_PERFORMANCE,
                ReviewItemSource.ANALYTICS,
            ),
            ordering_rule=("SEVERITY_THEN_CATEGORY_THEN_CODE_THEN_SYMBOL_DATE_V1"),
        ),
    )


@pytest.mark.django_db
def test_review_items_endpoint_is_owner_scoped_and_passes_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="review-items-api@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=owner,
        name="Review Items API",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        review_items_views,
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
        review_items_views,
        "get_asset_resolver",
        lambda: object(),
    )
    monkeypatch.setattr(
        review_items_views,
        "get_trading_session_calendar",
        FixedCalendar,
    )
    monkeypatch.setattr(
        review_items_views,
        "get_current_time",
        lambda: FIXED_NOW,
    )

    def fake_build(**kwargs: object) -> DashboardReviewItemsResult:
        captured.update(kwargs)
        return review_result()

    monkeypatch.setattr(
        review_items_views,
        "build_owned_portfolio_dashboard_review_items",
        fake_build,
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-review-items",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-16",
            "severity": "warning",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["counts"]["total"] == 1
    assert response.data["filtered_count"] == 1
    assert response.data["items"][0]["code"] == "STALE_PRICE_USED"
    assert response.data["items"][0]["severity"] == "WARNING"
    assert response.data["items"][0]["category"] == "MARKET_DATA"
    assert response.data["items"][0]["drilldown"]["resource"] == "HOLDINGS"
    assert response.data["items"][0]["drilldown"]["symbol"] == "AAPL"

    assert captured["user"] == owner
    assert captured["portfolio_id"] == portfolio.id
    assert captured["severity"] is ReviewItemSeverity.WARNING
    assert captured["category"] is None


@pytest.mark.django_db
def test_review_items_endpoint_hides_another_users_portfolio() -> None:
    owner = User.objects.create_user(
        email="review-owner@example.com",
        password="test-password-123",
    )
    other = User.objects.create_user(
        email="review-other@example.com",
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
            "api-v1-portfolio-dashboard-review-items",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-16",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "PORTFOLIO_NOT_FOUND"


@pytest.mark.django_db
def test_review_items_endpoint_rejects_unknown_filter() -> None:
    owner = User.objects.create_user(
        email="review-filter@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Review Filter",
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-review-items",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-16",
            "severity": "critical",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "severity" in response.data["errors"]
