"""Property tests for market-data coverage and missingness diagnostics."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.config import MAX_MISSING_EXPECTED_OBSERVATION_RATIO
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_quality import (
    MarketDataQualityDiagnosticCode,
    diagnose_price_frame_quality,
)

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)


def make_frame(trade_dates: tuple[date, ...]) -> PriceFrame:
    return tuple(
        PriceBar(
            asset_id=ASSET_ID,
            trade_date=trade_date,
            open=100.0,
            high=103.0,
            low=99.0,
            close=102.0,
            adjusted_close=101.5,
            volume=1_000_000,
            source="property-test",
            retrieved_at=RETRIEVED_AT,
        )
        for trade_date in trade_dates
    )


@given(
    expected_count=st.integers(min_value=2, max_value=30),
    missing_count=st.integers(min_value=0, max_value=30),
)
def test_excessive_missingness_follows_centralized_threshold(
    expected_count: int,
    missing_count: int,
) -> None:
    bounded_missing_count = min(missing_count, expected_count)
    start = date(2025, 1, 1)
    expected = tuple(start + timedelta(days=index) for index in range(expected_count))
    observed = expected[bounded_missing_count:]

    diagnostics = diagnose_price_frame_quality(
        make_frame(observed),
        requested_start=start,
        requested_end=start + timedelta(days=expected_count),
        expected_trade_dates=expected,
    )
    codes = {diagnostic.code for diagnostic in diagnostics}

    expected_ratio = bounded_missing_count / expected_count

    assert (MarketDataQualityDiagnosticCode.EXCESSIVE_MISSING_OBSERVATIONS in codes) is (
        expected_ratio > MAX_MISSING_EXPECTED_OBSERVATION_RATIO
    )


@given(
    gap_days=st.integers(min_value=0, max_value=5),
)
def test_non_expected_calendar_days_do_not_create_missingness(
    gap_days: int,
) -> None:
    start = date(2025, 1, 1)
    first_trade_date = start
    second_trade_date = start + timedelta(days=gap_days + 1)
    expected = (first_trade_date, second_trade_date)

    diagnostics = diagnose_price_frame_quality(
        make_frame(expected),
        requested_start=start,
        requested_end=second_trade_date + timedelta(days=1),
        expected_trade_dates=expected,
    )

    assert diagnostics == ()
