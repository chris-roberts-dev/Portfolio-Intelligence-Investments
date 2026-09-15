"""Deterministic US-equity trading-session calendar for the USD MVP.

The calendar models full-day US equity exchange closures required by current
portfolio valuation and daily performance. Early-close sessions remain trading
sessions because the market has an official daily close observation.

The application's bounded market-data history currently limits operational use
to modern history. Known unscheduled full-day closures within that horizon are
listed explicitly so they cannot be mistaken for missing market observations.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

_MONDAY = 0
_THURSDAY = 3
_SATURDAY = 5
_SUNDAY = 6

_SPECIAL_FULL_DAY_CLOSURES = frozenset(
    {
        date(2001, 9, 11),
        date(2001, 9, 12),
        date(2001, 9, 13),
        date(2001, 9, 14),
        date(2004, 6, 11),
        date(2007, 1, 2),
        date(2012, 10, 29),
        date(2012, 10, 30),
        date(2018, 12, 5),
        date(2025, 1, 9),
    }
)


class UsEquityTradingSessionCalendar:
    """Return regular US equity trading-session dates in ascending order."""

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        """Return the last ``count`` sessions on or before ``as_of_date``."""
        if count < 1:
            raise ValueError("count must be positive")

        sessions: list[date] = []
        candidate = as_of_date

        while len(sessions) < count:
            if self.is_session(candidate):
                sessions.append(candidate)

            candidate -= timedelta(days=1)

        sessions.reverse()
        return tuple(sessions)

    def is_session(self, session_date: date) -> bool:
        """Return whether ``session_date`` is a regular US equity session."""
        if session_date.weekday() >= _SATURDAY:
            return False

        return session_date not in _full_day_closures(session_date.year)


@lru_cache(maxsize=64)
def _full_day_closures(year: int) -> frozenset[date]:
    closures = {
        _new_years_day(year),
        _nth_weekday(year, 1, _MONDAY, 3),
        _nth_weekday(year, 2, _MONDAY, 3),
        _easter_sunday(year) - timedelta(days=2),
        _last_weekday(year, 5, _MONDAY),
        _nearest_weekday(date(year, 7, 4)),
        _nth_weekday(year, 9, _MONDAY, 1),
        _nth_weekday(year, 11, _THURSDAY, 4),
        _nearest_weekday(date(year, 12, 25)),
    }

    if year >= 2022:
        closures.add(_nearest_weekday(date(year, 6, 19)))

    closures.update(closure for closure in _SPECIAL_FULL_DAY_CLOSURES if closure.year == year)
    return frozenset(closures)


def _new_years_day(year: int) -> date:
    holiday = date(year, 1, 1)

    if holiday.weekday() == _SUNDAY:
        return holiday + timedelta(days=1)

    return holiday


def _nearest_weekday(holiday: date) -> date:
    if holiday.weekday() == _SATURDAY:
        return holiday - timedelta(days=1)

    if holiday.weekday() == _SUNDAY:
        return holiday + timedelta(days=1)

    return holiday


def _nth_weekday(
    year: int,
    month: int,
    weekday: int,
    occurrence: int,
) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(
    year: int,
    month: int,
    weekday: int,
) -> date:
    first_next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    last = first_next_month - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def _easter_sunday(year: int) -> date:
    """Return Gregorian Easter using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = (h + ell - 7 * m + 114) % 31 + 1
    return date(year, month, day)
