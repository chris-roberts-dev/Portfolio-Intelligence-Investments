"""API coverage for the dashboard portfolio performance endpoint."""

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
from apps.market_data.services.asset_resolution import (
    InMemoryAssetResolver,
)
from apps.portfolios.api import performance_views
from apps.portfolios.models import Portfolio
from apps.portfolios.services.dashboard_performance import (
    DashboardPerformanceProvenance,
    DashboardPerformanceResult,
    PerformanceDataQualityState,
    PortfolioPerformancePoint,
    PortfolioPerformanceSummary,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000000601")
FIXED_NOW = datetime(2026, 1, 6, 23, tzinfo=UTC)


class FixedTradingCalendar:
    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        del count
        sessions = (
            date(2026, 1, 2),
            date(2026, 1, 5),
            date(2026, 1, 6),
        )
        return tuple(session for session in sessions if session <= as_of_date)


def result() -> DashboardPerformanceResult:
    points = (
        PortfolioPerformancePoint(
            observation_date=date(2026, 1, 2),
            portfolio_value=Decimal("1000.00"),
            net_external_flow=Decimal("0"),
            daily_return=None,
            cumulative_return=0.0,
            data_quality=PerformanceDataQualityState.CURRENT,
            warnings=(),
        ),
        PortfolioPerformancePoint(
            observation_date=date(2026, 1, 5),
            portfolio_value=Decimal("1100.00"),
            net_external_flow=Decimal("0"),
            daily_return=0.10,
            cumulative_return=0.10,
            data_quality=PerformanceDataQualityState.CURRENT,
            warnings=(),
        ),
    )
    return DashboardPerformanceResult(
        summary=PortfolioPerformanceSummary(
            starting_value=Decimal("1000.00"),
            ending_value=Decimal("1100.00"),
            value_change=Decimal("100.00"),
            net_external_flow=Decimal("0"),
            investment_gain_loss=Decimal("100.00"),
            cumulative_return=0.10,
            benchmark_cumulative_return=None,
        ),
        points=points,
        benchmark_points=(),
        portfolio_data_quality=PerformanceDataQualityState.CURRENT,
        benchmark_data_quality=None,
        warnings=(),
        provenance=DashboardPerformanceProvenance(
            portfolio_id=PORTFOLIO_ID,
            base_currency="USD",
            provider="mock",
            requested_start=date(2026, 1, 1),
            requested_end_exclusive=date(2026, 1, 6),
            effective_start=date(2026, 1, 2),
            effective_end_exclusive=date(2026, 1, 6),
            data_as_of=datetime(2026, 1, 5, 22, tzinfo=UTC),
            calculated_at=FIXED_NOW,
            engine_version="0.1.0.dev0",
            price_field="adjusted_close",
            benchmark_asset_id=None,
            benchmark_symbol=None,
        ),
    )


@pytest.mark.django_db
def test_performance_endpoint_is_owner_scoped_and_serializes_exact_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = User.objects.create_user(
        email="performance-api@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=owner,
        name="Performance API",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        performance_views,
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
        performance_views,
        "get_asset_resolver",
        lambda: InMemoryAssetResolver(()),
    )
    monkeypatch.setattr(
        performance_views,
        "get_trading_session_calendar",
        FixedTradingCalendar,
    )
    monkeypatch.setattr(
        performance_views,
        "get_current_time",
        lambda: FIXED_NOW,
    )

    def fake_build(
        **kwargs: object,
    ) -> DashboardPerformanceResult:
        captured.update(kwargs)
        return result()

    monkeypatch.setattr(
        performance_views,
        "build_owned_portfolio_dashboard_performance",
        fake_build,
    )

    response = client.get(
        reverse(
            "api-v1-portfolio-performance",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-01-01",
            "end": "2026-01-06",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["summary"]["starting_value"] == "1000.00"
    assert response.data["summary"]["ending_value"] == "1100.00"
    assert response.data["summary"]["cumulative_return"] == pytest.approx(0.10)
    assert response.data["points"][0]["portfolio_value"] == "1000.00"
    assert response.data["points"][0]["cumulative_return"] == pytest.approx(0.0)
    assert response.data["provenance"]["base_currency"] == "USD"
    assert response.data["provenance"]["provider"] == "mock"
    assert captured["user"] == owner
    assert captured["portfolio_id"] == portfolio.id
    assert captured["requested_start"] == date(2026, 1, 1)
    assert captured["requested_end"] == date(2026, 1, 6)


@pytest.mark.django_db
def test_performance_endpoint_rejects_invalid_range() -> None:
    owner = User.objects.create_user(
        email="performance-range@example.com",
        password="test-password-123",
    )
    portfolio = Portfolio.objects.create(
        user=owner,
        name="Performance Range",
    )
    client = APIClient()
    client.force_authenticate(user=owner)
    url = reverse(
        "api-v1-portfolio-performance",
        kwargs={"portfolio_id": portfolio.id},
    )

    response = client.get(
        url,
        {
            "start": "2026-01-05",
            "end": "2026-01-05",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "VALIDATION_ERROR"
    assert "end" in response.data["errors"]
