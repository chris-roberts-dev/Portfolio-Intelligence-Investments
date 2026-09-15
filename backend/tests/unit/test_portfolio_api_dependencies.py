"""Tests for concrete dependencies used by provider-backed portfolio reads."""

from apps.assets.resolution import DjangoAssetResolver
from apps.portfolios.api.dependencies import (
    get_asset_resolver,
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
