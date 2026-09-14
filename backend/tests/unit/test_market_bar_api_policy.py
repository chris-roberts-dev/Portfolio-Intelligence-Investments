"""Unit tests for market-bar API throttling and provider authorization."""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.market_data.api.policies import (
    DEFAULT_MARKET_DATA_BAR_QUERY_THROTTLE_RATE,
    MarketBarQueryThrottle,
    MarketDataProviderAuthorizationError,
    authorize_market_data_provider_request,
    get_market_bar_query_throttle_rate,
)


def test_throttle_rate_uses_default_when_no_override_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "MARKET_DATA_BAR_QUERY_THROTTLE_RATE",
        raising=False,
    )

    assert get_market_bar_query_throttle_rate() == DEFAULT_MARKET_DATA_BAR_QUERY_THROTTLE_RATE


def test_throttle_rate_can_be_environment_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MARKET_DATA_BAR_QUERY_THROTTLE_RATE",
        "25/min",
    )

    assert get_market_bar_query_throttle_rate() == "25/min"


@override_settings(MARKET_DATA_BAR_QUERY_THROTTLE_RATE="7/min")
def test_throttle_rate_prefers_django_setting() -> None:
    assert get_market_bar_query_throttle_rate() == "7/min"
    assert MarketBarQueryThrottle().get_rate() == "7/min"


@override_settings(MARKET_DATA_BAR_QUERY_THROTTLE_RATE="invalid")
def test_invalid_throttle_rate_fails_configuration() -> None:
    with pytest.raises(ImproperlyConfigured):
        get_market_bar_query_throttle_rate()


def test_authenticated_user_may_use_default_provider() -> None:
    authorize_market_data_provider_request(
        requested_provider="mock",
        default_provider="mock",
        is_authenticated=True,
        is_staff=False,
    )


def test_implicit_default_provider_needs_no_elevated_authorization() -> None:
    authorize_market_data_provider_request(
        requested_provider=None,
        default_provider="mock",
        is_authenticated=True,
        is_staff=False,
    )


def test_staff_user_may_request_non_default_provider() -> None:
    authorize_market_data_provider_request(
        requested_provider="yfinance",
        default_provider="mock",
        is_authenticated=True,
        is_staff=True,
    )


def test_non_staff_user_cannot_request_non_default_provider() -> None:
    with pytest.raises(
        MarketDataProviderAuthorizationError,
        match="staff authorization",
    ):
        authorize_market_data_provider_request(
            requested_provider="yfinance",
            default_provider="mock",
            is_authenticated=True,
            is_staff=False,
        )
