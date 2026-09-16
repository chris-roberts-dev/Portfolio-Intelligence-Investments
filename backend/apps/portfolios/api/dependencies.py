"""Dependency boundaries for owned-portfolio read APIs."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
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
    """Return the timezone-aware clock used by current-holdings reads.

    Normal application settings use wall-clock time. The isolated deterministic
    demo settings may provide ``PORTFOLIO_FIXED_CURRENT_TIME`` so committed CSV
    fixtures remain reproducible for local demonstrations and browser tests.
    """
    fixed_time = getattr(settings, "PORTFOLIO_FIXED_CURRENT_TIME", None)

    if fixed_time is None:
        return timezone.now()

    if not isinstance(fixed_time, datetime) or timezone.is_naive(fixed_time):
        raise TradingSessionCalendarUnavailable(
            "PORTFOLIO_FIXED_CURRENT_TIME must be a timezone-aware datetime."
        )

    return fixed_time
