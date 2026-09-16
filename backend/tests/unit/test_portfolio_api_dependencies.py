"""Tests for concrete dependencies used by provider-backed portfolio reads."""

from datetime import UTC, datetime

import pytest
from django.test import override_settings

from apps.assets.resolution import DjangoAssetResolver
from apps.portfolios.api.dependencies import (
    TradingSessionCalendarUnavailable,
    get_asset_resolver,
    get_current_time,
    get_trading_session_calendar,
)
from apps.portfolios.services.trading_calendar import (
    UsEquityTradingSessionCalendar,
)


def test_portfolio_api_uses_persisted_asset_resolver() -> None:
    assert isinstance(get_asset_resolver(), DjangoAssetResolver)


def test_portfolio_api_uses_us_equity_trading_calendar() -> None:
    assert isinstance(
        get_trading_session_calendar(),
        UsEquityTradingSessionCalendar,
    )


@override_settings(PORTFOLIO_FIXED_CURRENT_TIME=datetime(2026, 9, 16, 16, 0, tzinfo=UTC))
def test_portfolio_api_can_use_explicit_deterministic_clock() -> None:
    assert get_current_time() == datetime(2026, 9, 16, 16, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "invalid_value",
    (
        "2026-09-16T16:00:00Z",
        datetime(2026, 9, 16, 16, 0),
    ),
)
def test_portfolio_api_rejects_invalid_deterministic_clock(
    invalid_value: object,
) -> None:
    with (
        override_settings(PORTFOLIO_FIXED_CURRENT_TIME=invalid_value),
        pytest.raises(TradingSessionCalendarUnavailable),
    ):
        get_current_time()
