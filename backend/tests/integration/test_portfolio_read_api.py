"""Deterministic API tests for authenticated owned-portfolio read endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.market_data.providers.configuration import (
    ProviderConfigurationError,
    ProviderConfigurationErrorCode,
)
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.services.asset_resolution import InMemoryAssetResolver
from apps.portfolios.api import views
from apps.portfolios.api.dependencies import TradingSessionCalendarUnavailable
from apps.portfolios.models import Portfolio
from apps.portfolios.services.analytics import (
    PortfolioAnalyticsResult,
    PortfolioAnalyticsWarning,
    PortfolioAnalyticsWarningCode,
)
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentValuationProvenance,
)
from apps.portfolios.services.ledger import LedgerReplayResult
from portfolio_engine.contracts.analytical_result import AnalyticalResultProvenance
from portfolio_engine.portfolio.allocation import PortfolioAllocationResult
from portfolio_engine.portfolio.valuation import PortfolioValuationResult

FIXED_NOW = datetime(2026, 9, 15, 21, tzinfo=UTC)
PROVIDER_RETRIEVED_AT = datetime(2026, 9, 15, 20, tzinfo=UTC)


class FixedTradingCalendar:
    """Deterministic API-test trading-session calendar."""

    def __init__(self, sessions: tuple[date, ...]) -> None:
        self._sessions = sessions

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        eligible = tuple(session for session in self._sessions if session <= as_of_date)
        return eligible[-count:]


@pytest.fixture
def owner() -> User:
    return User.objects.create_user(
        email="portfolio-api-owner@example.com",
        password="test-password-123",
    )


@pytest.fixture
def other_user() -> User:
    return User.objects.create_user(
        email="portfolio-api-other@example.com",
        password="test-password-123",
    )


@pytest.fixture
def portfolio(owner: User) -> Portfolio:
    return Portfolio.objects.create(
        user=owner,
        name="Owner Portfolio",
    )


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def mock_provider() -> MockMarketDataProvider:
    return MockMarketDataProvider(
        {},
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )


def install_provider_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    calendar: FixedTradingCalendar | None = None,
) -> None:
    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        lambda _requested_provider=None, **_kwargs: mock_provider(),
    )
    monkeypatch.setattr(
        views,
        "get_asset_resolver",
        lambda: InMemoryAssetResolver(()),
    )
    monkeypatch.setattr(
        views,
        "get_current_time",
        lambda: FIXED_NOW,
    )

    if calendar is not None:
        monkeypatch.setattr(
            views,
            "get_trading_session_calendar",
            lambda: calendar,
        )


def current_result(portfolio_id: UUID) -> CurrentPortfolioValuationResult:
    valuation = PortfolioValuationResult(
        positions=(),
        security_market_value=0.0,
        cash_value=500.0,
        total_market_value=500.0,
    )
    allocation = PortfolioAllocationResult(
        positions=(),
        cash_value=500.0,
        cash_weight=1.0,
        total_market_value=500.0,
        weight_sum=1.0,
        weight_sum_tolerance=1e-8,
    )
    return CurrentPortfolioValuationResult(
        ledger=LedgerReplayResult(
            portfolio_id=portfolio_id,
            as_of=FIXED_NOW,
            cash_balance=Decimal("500.00000000"),
            positions=(),
            cash_flows=(),
            net_external_cash_flow=Decimal("500.00000000"),
            net_internal_cash_flow=Decimal("0"),
            transaction_count=1,
        ),
        provenance=CurrentValuationProvenance(
            portfolio_id=portfolio_id,
            benchmark_asset_id=None,
            provider="mock",
            as_of=FIXED_NOW,
            retrieved_at=None,
            price_field="close",
        ),
        prices=(),
        warnings=(),
        is_complete=True,
        valuation=valuation,
        allocation=allocation,
    )


def analytics_result(portfolio_id: UUID) -> PortfolioAnalyticsResult:
    warning = PortfolioAnalyticsWarning(
        code=PortfolioAnalyticsWarningCode.INSUFFICIENT_HISTORY,
        message="Insufficient history.",
        observations=1,
    )
    return PortfolioAnalyticsResult(
        portfolio_id=portfolio_id,
        observations=1,
        benchmark_observations=None,
        cumulative_return=0.0,
        cagr=None,
        annualized_volatility=None,
        sharpe=None,
        sortino=None,
        maximum_drawdown=None,
        beta=None,
        current_allocation=None,
        concentration=None,
        provenance=AnalyticalResultProvenance(
            as_of_date=date(2026, 1, 5),
            period_start=date(2026, 1, 2),
            period_end=date(2026, 1, 5),
            data_source="mock",
            price_field="adjusted_close",
            annualization_factor=252.0,
            benchmark=None,
            warnings=(warning.message,),
        ),
        warnings=(warning,),
    )


@pytest.mark.django_db
def test_portfolio_list_and_detail_are_owner_scoped(
    owner: User,
    other_user: User,
    portfolio: Portfolio,
) -> None:
    other_portfolio = Portfolio.objects.create(
        user=other_user,
        name="Other Portfolio",
    )
    client = authenticated_client(owner)

    list_response = client.get(reverse("api-v1-portfolio-list"))
    detail_response = client.get(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": portfolio.id},
        )
    )
    hidden_response = client.get(
        reverse(
            "api-v1-portfolio-detail",
            kwargs={"portfolio_id": other_portfolio.id},
        )
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in list_response.data] == [str(portfolio.id)]
    assert detail_response.status_code == status.HTTP_200_OK
    assert detail_response.data["id"] == str(portfolio.id)
    assert hidden_response.status_code == status.HTTP_404_NOT_FOUND
    assert hidden_response.data == {
        "code": "PORTFOLIO_NOT_FOUND",
        "detail": "Portfolio was not found.",
    }


@pytest.mark.django_db
def test_current_holdings_delegates_to_owned_application_service(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    install_provider_dependencies(monkeypatch)
    captured: dict[str, object] = {}

    def fake_value_owned_portfolio(
        **kwargs: object,
    ) -> CurrentPortfolioValuationResult:
        captured.update(kwargs)
        return current_result(portfolio.id)

    monkeypatch.setattr(
        views,
        "value_owned_portfolio",
        fake_value_owned_portfolio,
    )

    response = authenticated_client(owner).get(
        reverse(
            "api-v1-portfolio-holdings",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["portfolio_id"] == str(portfolio.id)
    assert response.data["cash_balance"] == "500.00000000"
    assert captured["user"] == owner
    assert captured["portfolio_id"] == portfolio.id
    assert captured["as_of"] == FIXED_NOW
    assert captured["provider_name"] == "mock"


@pytest.mark.django_db
@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="mock",
    MARKET_DATA_ALLOWED_PROVIDERS=("mock", "yfinance"),
)
def test_non_default_provider_requires_explicit_authorization(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    provider_resolution_called = False

    def fail_if_resolved(
        _requested_provider=None,
        **_kwargs: object,
    ) -> MockMarketDataProvider:
        nonlocal provider_resolution_called
        provider_resolution_called = True
        raise AssertionError("provider resolution should not be attempted")

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        fail_if_resolved,
    )

    response = authenticated_client(owner).get(
        reverse(
            "api-v1-portfolio-holdings",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"provider": "yfinance"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "NON_DEFAULT_PROVIDER_FORBIDDEN"
    assert not provider_resolution_called


@pytest.mark.django_db
@override_settings(
    MARKET_DATA_DEFAULT_PROVIDER="mock",
    MARKET_DATA_ALLOWED_PROVIDERS=("mock", "yfinance"),
)
def test_staff_cannot_bypass_server_side_provider_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    owner.is_staff = True
    owner.save(update_fields=["is_staff"])

    def reject_provider(
        _requested_provider=None,
        **_kwargs: object,
    ) -> MockMarketDataProvider:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.PROVIDER_NOT_ALLOWED,
            "Provider 'other' is not allowed.",
            provider_name="other",
        )

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        reject_provider,
    )

    response = authenticated_client(owner).get(
        reverse(
            "api-v1-portfolio-holdings",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"provider": "other"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "PROVIDER_NOT_ALLOWED"
    assert "provider" in response.data["errors"]


@pytest.mark.django_db
def test_default_provider_unavailable_returns_503(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    def unavailable_provider(
        _requested_provider=None,
        **_kwargs: object,
    ) -> MockMarketDataProvider:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.DEFAULT_PROVIDER_UNREGISTERED,
            "Configured default provider is unavailable.",
            provider_name="mock",
        )

    monkeypatch.setattr(
        views,
        "resolve_market_data_provider",
        unavailable_provider,
    )

    response = authenticated_client(owner).get(
        reverse(
            "api-v1-portfolio-holdings",
            kwargs={"portfolio_id": portfolio.id},
        )
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data == {
        "code": "DEFAULT_PROVIDER_UNREGISTERED",
        "detail": "Configured default provider is unavailable.",
    }


@pytest.mark.django_db
def test_analytics_endpoint_builds_only_requested_trading_session_valuations(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    calendar = FixedTradingCalendar(
        (
            date(2025, 12, 31),
            date(2026, 1, 2),
            date(2026, 1, 5),
            date(2026, 1, 6),
        )
    )
    install_provider_dependencies(
        monkeypatch,
        calendar=calendar,
    )
    captured: dict[str, object] = {}

    def fake_analyze_owned_portfolio(
        **kwargs: object,
    ) -> PortfolioAnalyticsResult:
        captured.update(kwargs)
        return analytics_result(portfolio.id)

    monkeypatch.setattr(
        views,
        "analyze_owned_portfolio",
        fake_analyze_owned_portfolio,
    )

    response = authenticated_client(owner).get(
        reverse(
            "api-v1-portfolio-analytics",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {
            "start": "2026-01-01",
            "end": "2026-01-06",
            "risk_free_rate_annual": "0.02",
            "minimum_acceptable_return_annual": "0.01",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["portfolio_id"] == str(portfolio.id)
    assert captured["valuation_times"] == (
        datetime.combine(date(2026, 1, 2), datetime.max.time(), tzinfo=UTC),
        datetime.combine(date(2026, 1, 5), datetime.max.time(), tzinfo=UTC),
    )
    assert captured["risk_free_rate_annual"] == pytest.approx(0.02)
    assert captured["minimum_acceptable_return_annual"] == pytest.approx(0.01)


@pytest.mark.django_db
def test_analytics_endpoint_rejects_invalid_or_too_short_period(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    calendar = FixedTradingCalendar((date(2026, 1, 2),))
    install_provider_dependencies(
        monkeypatch,
        calendar=calendar,
    )
    client = authenticated_client(owner)
    url = reverse(
        "api-v1-portfolio-analytics",
        kwargs={"portfolio_id": portfolio.id},
    )

    invalid_range = client.get(
        url,
        {"start": "2026-01-05", "end": "2026-01-05"},
    )
    short_range = client.get(
        url,
        {"start": "2026-01-01", "end": "2026-01-03"},
    )

    assert invalid_range.status_code == status.HTTP_400_BAD_REQUEST
    assert invalid_range.data["code"] == "VALIDATION_ERROR"
    assert "end" in invalid_range.data["errors"]
    assert short_range.status_code == status.HTTP_400_BAD_REQUEST
    assert short_range.data["code"] == "INSUFFICIENT_ANALYTICS_PERIOD"


@pytest.mark.django_db
def test_trading_calendar_unavailability_still_maps_to_503(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    install_provider_dependencies(monkeypatch)

    def unavailable_calendar() -> FixedTradingCalendar:
        raise TradingSessionCalendarUnavailable("No trading-session calendar is configured.")

    monkeypatch.setattr(
        views,
        "get_trading_session_calendar",
        unavailable_calendar,
    )

    response = authenticated_client(owner).get(
        reverse(
            "api-v1-portfolio-analytics",
            kwargs={"portfolio_id": portfolio.id},
        ),
        {"start": "2026-01-01", "end": "2026-01-06"},
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data["code"] == "TRADING_CALENDAR_UNAVAILABLE"


@pytest.mark.django_db
@override_settings(MARKET_DATA_BAR_QUERY_THROTTLE_RATE="1/min")
def test_provider_backed_portfolio_read_is_throttled(
    monkeypatch: pytest.MonkeyPatch,
    owner: User,
    portfolio: Portfolio,
) -> None:
    cache.clear()
    install_provider_dependencies(monkeypatch)
    monkeypatch.setattr(
        views,
        "value_owned_portfolio",
        lambda **_kwargs: current_result(portfolio.id),
    )
    client = authenticated_client(owner)
    url = reverse(
        "api-v1-portfolio-holdings",
        kwargs={"portfolio_id": portfolio.id},
    )

    try:
        first_response = client.get(url)
        second_response = client.get(url)
    finally:
        cache.clear()

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
