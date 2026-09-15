"""Dependency boundaries for owned-portfolio read APIs."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from apps.market_data.api.dependencies import (
    get_asset_resolver as get_market_data_asset_resolver,
)
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.services.current_valuation import TradingSessionCalendar
from apps.portfolios.services.trading_calendar import (
    UsEquityTradingSessionCalendar,
)


class TradingSessionCalendarUnavailable(RuntimeError):
    """Raised when a required trading-session calendar cannot be supplied."""

    code = "TRADING_CALENDAR_UNAVAILABLE"


_US_EQUITY_TRADING_SESSION_CALENDAR = UsEquityTradingSessionCalendar()


def get_asset_resolver() -> AssetResolver:
    """Reuse the persisted provider-neutral market-data resolver boundary."""
    return get_market_data_asset_resolver()


def get_trading_session_calendar() -> TradingSessionCalendar:
    """Return the deterministic US-equity calendar used by the USD MVP."""
    return _US_EQUITY_TRADING_SESSION_CALENDAR


def get_current_time() -> datetime:
    """Return the timezone-aware clock used by current-holdings reads."""
    return timezone.now()
