"""Dependency boundaries for owned-portfolio read APIs."""

from __future__ import annotations

from datetime import date, datetime

from django.utils import timezone

from apps.market_data.api.dependencies import (
    get_asset_resolver as get_market_data_asset_resolver,
)
from apps.market_data.services.asset_resolution import AssetResolver
from apps.portfolios.services.current_valuation import TradingSessionCalendar


class TradingSessionCalendarUnavailable(RuntimeError):
    """Raised when no concrete trading-session calendar is configured."""

    code = "TRADING_CALENDAR_UNAVAILABLE"


class _UnconfiguredTradingSessionCalendar:
    """Fail explicitly rather than approximating exchange sessions."""

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        del as_of_date, count
        raise TradingSessionCalendarUnavailable(
            "No trading-session calendar is configured for portfolio valuation."
        )


_UNCONFIGURED_TRADING_SESSION_CALENDAR = _UnconfiguredTradingSessionCalendar()


def get_asset_resolver() -> AssetResolver:
    """Reuse the existing provider-neutral market-data resolver boundary."""
    return get_market_data_asset_resolver()


def get_trading_session_calendar() -> TradingSessionCalendar:
    """Return the configured trading-session calendar boundary.

    A concrete exchange calendar has not yet been introduced. Returning a
    fail-explicit implementation avoids silently treating weekdays or holidays
    as authoritative trading sessions.
    """
    return _UNCONFIGURED_TRADING_SESSION_CALENDAR


def get_current_time() -> datetime:
    """Return the timezone-aware clock used by current-holdings reads."""
    return timezone.now()
