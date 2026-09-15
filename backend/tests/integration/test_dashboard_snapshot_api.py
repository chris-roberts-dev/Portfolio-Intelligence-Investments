"""API coverage for the canonical owner-scoped dashboard snapshot."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.portfolios.api import dashboard_snapshot_views
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_snapshot import (
    DashboardSnapshotContext,
    DashboardSnapshotModule,
    DashboardSnapshotModuleState,
    DashboardSnapshotModuleStatus,
    DashboardSnapshotResult,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001701")
FIXED_NOW = datetime(2026, 9, 16, 0, tzinfo=UTC)


class FixedCalendar:
    """Deterministic trading-session calendar for snapshot API tests."""

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
                date(2026, 9, 15),
                date(2026, 9, 16),
            )
            if session <= as_of_date
        )


def unavailable_modules() -> tuple[DashboardSnapshotModuleState, ...]:
    return tuple(
        DashboardSnapshotModuleState(
            module=module,
            status=DashboardSnapshotModuleStatus.UNAVAILABLE,
            error_code=f"{module.value}_UNAVAILABLE",
            detail="Module unavailable in deterministic API fixture.",
        )
        for module in DashboardSnapshotModule
    )


def snapshot_result() -> DashboardSnapshotResult:
    return DashboardSnapshotResult(
        snapshot=DashboardSnapshotContext(
            snapshot_id=uuid4(),
            portfolio_id=PORTFOLIO_ID,
            base_currency="USD",
            provider="mock",
            requested_start=date(2026, 9, 1),
            requested_end_exclusive=date(2026, 9, 17),
            effective_start=date(2026, 9, 1),
            effective_end_exclusive=date(2026, 9, 16),
            valuation_cutoff=FIXED_NOW,
            calculated_at=FIXED_NOW,
            engine_version="0.1.0.dev0",
            current_data_as_of=None,
            historical_data_as_of=None,
            analytics_as_of_date=None,
        ),
        is_complete=False,
        modules=unavailable_modules(),
        summary=None,
        performance=None,
        allocation=None,
        holdings=None,
        movers=None,
        analytics=None,
        review_items=None,
    )


@pytest.mark.django_db
def test_snapshot_endpoint_is_owner_scoped_and_uses_one_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="snapshot-api@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=owner,
        name="Snapshot API",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    captured: dict[str, object] = {}
    clock_calls = 0

    monkeypatch.setattr(
        dashboard_snapshot_views,
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
        dashboard_snapshot_views,
        "get_asset_resolver",
        lambda: object(),
    )
    monkeypatch.setattr(
        dashboard_snapshot_views,
        "get_trading_session_calendar",
        FixedCalendar,
    )

    def fixed_clock() -> datetime:
        nonlocal clock_calls
        clock_calls += 1
        return FIXED_NOW

    monkeypatch.setattr(
        dashboard_snapshot_views,
        "get_current_time",
        fixed_clock,
    )

    def fake_build(**kwargs: object) -> DashboardSnapshotResult:
        captured.update(kwargs)
        return snapshot_result()

    monkeypatch.setattr(
        dashboard_snapshot_views,
        "build_owned_portfolio_dashboard_snapshot",
        fake_build,
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-snapshot",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-17",
            "movers_limit": "7",
            "risk_free_rate_annual": "0.02",
            "minimum_acceptable_return_annual": "0.01",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["snapshot"]["portfolio_id"] == str(portfolio.id)
    assert response.data["snapshot"]["provider"] == "mock"
    assert response.data["is_complete"] is False
    assert response.data["summary"] is None
    assert len(response.data["modules"]) == len(DashboardSnapshotModule)

    assert clock_calls == 1
    assert captured["calculated_at"] == FIXED_NOW
    assert captured["valuation_times"] == (
        datetime(2026, 9, 1, 23, 59, 59, 999999, tzinfo=UTC),
        datetime(2026, 9, 15, 23, 59, 59, 999999, tzinfo=UTC),
    )
    assert captured["movers_limit"] == 7
    assert captured["risk_free_rate_annual"] == pytest.approx(0.02)
    assert captured["minimum_acceptable_return_annual"] == pytest.approx(0.01)


@pytest.mark.django_db
def test_snapshot_endpoint_hides_another_users_portfolio() -> None:
    owner = User.objects.create_user(
        email="snapshot-owner@example.com",
        password="test-password-123",
    )
    other = User.objects.create_user(
        email="snapshot-other@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=other,
        name="Other Snapshot",
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-snapshot",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-17",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["code"] == "PORTFOLIO_NOT_FOUND"


@pytest.mark.django_db
def test_snapshot_endpoint_rejects_range_without_two_completed_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="snapshot-cutoff@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Cutoff Snapshot",
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    monkeypatch.setattr(
        dashboard_snapshot_views,
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
        dashboard_snapshot_views,
        "get_trading_session_calendar",
        FixedCalendar,
    )
    monkeypatch.setattr(
        dashboard_snapshot_views,
        "get_current_time",
        lambda: datetime(2026, 9, 1, 12, tzinfo=UTC),
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-dashboard-snapshot",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-09-01",
            "end": "2026-09-17",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "INSUFFICIENT_DASHBOARD_PERIOD"
