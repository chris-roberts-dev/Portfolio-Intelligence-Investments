"""Release-gate coverage for the deterministic offline v0.1 sample workflow."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.portfolios.management.commands.seed_sample_portfolio import (
    SAMPLE_PORTFOLIO_ID,
    SAMPLE_SPY_ID,
    SAMPLE_USER_EMAIL,
)
from apps.portfolios.models import Portfolio


@pytest.mark.django_db
@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="csv",
    MARKET_DATA_ALLOWED_PROVIDERS=("csv",),
    PORTFOLIO_FIXED_CURRENT_TIME=datetime(2026, 9, 16, 16, 0, tzinfo=UTC),
)
def test_sample_portfolio_exposes_required_v01_dashboard_and_analytics() -> None:
    call_command("seed_sample_portfolio", reset=True, verbosity=0)

    user = User.objects.get(email=SAMPLE_USER_EMAIL)
    portfolio = Portfolio.objects.get(id=SAMPLE_PORTFOLIO_ID)

    assert portfolio.user == user
    assert portfolio.benchmark_asset_id == SAMPLE_SPY_ID

    client = APIClient()
    client.force_authenticate(user=user)

    dashboard = client.get(
        reverse(
            "api-v1-portfolio-dashboard-snapshot",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-03-16",
            "end": "2026-09-17",
        },
    )

    assert dashboard.status_code == status.HTTP_200_OK
    assert dashboard.data["summary"] is not None
    assert dashboard.data["performance"] is not None
    assert dashboard.data["allocation"] is not None
    assert dashboard.data["holdings"] is not None
    assert dashboard.data["performance"]["summary"]["ending_value"] is not None
    assert dashboard.data["performance"]["summary"]["cumulative_return"] is not None
    assert dashboard.data["performance"]["summary"]["benchmark_cumulative_return"] is not None

    analytics = client.get(
        reverse(
            "api-v1-portfolio-analytics",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-03-16",
            "end": "2026-09-16",
            "rolling_window": "21",
        },
    )

    assert analytics.status_code == status.HTTP_200_OK
    payload = analytics.data

    assert payload["cumulative_return"] is not None
    assert payload["cagr"] is not None
    assert payload["cagr"]["value"] is not None
    assert payload["annualized_volatility"] is not None
    assert payload["sharpe"] is not None
    assert payload["sharpe"]["value"] is not None
    assert payload["sortino"] is not None
    assert payload["sortino"]["value"] is not None
    assert payload["maximum_drawdown"] is not None
    assert payload["maximum_drawdown"]["value"] is not None
    assert payload["beta"] is not None
    assert payload["beta"]["value"] is not None
    assert payload["benchmark_correlation"] is not None
    assert payload["benchmark_correlation"]["value"] is not None
    assert payload["rolling_return_window"] == 21
    assert payload["rolling_returns"]
    assert payload["current_allocation"] is not None
    assert payload["concentration"] is not None
    assert payload["provenance"]["benchmark"] == "SPY"
    assert payload["provenance"]["data_source"] == "csv"
