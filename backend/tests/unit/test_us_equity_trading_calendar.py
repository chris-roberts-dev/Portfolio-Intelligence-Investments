"""Unit tests for the deterministic US-equity trading-session calendar."""

from datetime import date

import pytest

from apps.portfolios.services.trading_calendar import (
    UsEquityTradingSessionCalendar,
)


def test_sessions_exclude_weekends_and_independence_day_observance() -> None:
    calendar = UsEquityTradingSessionCalendar()

    assert calendar.sessions_through(
        date(2026, 7, 6),
        count=5,
    ) == (
        date(2026, 6, 29),
        date(2026, 6, 30),
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 6),
    )


def test_good_friday_is_not_a_trading_session() -> None:
    calendar = UsEquityTradingSessionCalendar()

    assert calendar.sessions_through(
        date(2026, 4, 6),
        count=3,
    ) == (
        date(2026, 4, 1),
        date(2026, 4, 2),
        date(2026, 4, 6),
    )


def test_known_national_day_of_mourning_is_not_a_session() -> None:
    calendar = UsEquityTradingSessionCalendar()

    assert calendar.sessions_through(
        date(2025, 1, 10),
        count=3,
    ) == (
        date(2025, 1, 7),
        date(2025, 1, 8),
        date(2025, 1, 10),
    )


def test_weekend_as_of_returns_last_prior_session() -> None:
    calendar = UsEquityTradingSessionCalendar()

    assert calendar.sessions_through(
        date(2026, 7, 5),
        count=1,
    ) == (date(2026, 7, 2),)


def test_saturday_new_year_does_not_close_prior_friday() -> None:
    calendar = UsEquityTradingSessionCalendar()

    assert calendar.is_session(date(2021, 12, 31))


def test_juneteenth_is_a_trading_holiday_from_2022() -> None:
    calendar = UsEquityTradingSessionCalendar()

    assert not calendar.is_session(date(2026, 6, 19))


def test_session_count_must_be_positive() -> None:
    calendar = UsEquityTradingSessionCalendar()

    with pytest.raises(ValueError, match="count must be positive"):
        calendar.sessions_through(
            date(2026, 1, 2),
            count=0,
        )
