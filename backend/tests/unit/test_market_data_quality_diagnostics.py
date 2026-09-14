"""Unit tests for market-data coverage and missingness diagnostics."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.config import MAX_MISSING_EXPECTED_OBSERVATION_RATIO
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_quality import (
    MarketDataQualityDiagnosticCode,
    diagnose_price_frame_quality,
)
from portfolio_engine.contracts.market_data_validation import MarketDataQualityError

ASSET_ID = UUID("00000000-0000-0000-0000-000000000001")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)


def make_frame(*trade_dates: date) -> PriceFrame:
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
            source="test",
            retrieved_at=RETRIEVED_AT,
        )
        for trade_date in trade_dates
    )


def diagnostic_codes(
    frame: PriceFrame,
    expected: tuple[date, ...],
) -> set[MarketDataQualityDiagnosticCode]:
    diagnostics = diagnose_price_frame_quality(
        frame,
        requested_start=date(2026, 1, 1),
        requested_end=date(2026, 1, 12),
        expected_trade_dates=expected,
    )
    return {diagnostic.code for diagnostic in diagnostics}


def test_complete_expected_coverage_has_no_diagnostics() -> None:
    expected = (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
        date(2026, 1, 8),
        date(2026, 1, 9),
    )

    assert diagnostic_codes(make_frame(*expected), expected) == set()


def test_weekends_are_not_inferred_as_missing_observations() -> None:
    expected = (
        date(2026, 1, 2),
        date(2026, 1, 5),
    )

    diagnostics = diagnose_price_frame_quality(
        make_frame(*expected),
        requested_start=date(2026, 1, 2),
        requested_end=date(2026, 1, 6),
        expected_trade_dates=expected,
    )

    assert diagnostics == ()


def test_missing_first_expected_trade_date_flags_truncated_start() -> None:
    expected = (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    )

    codes = diagnostic_codes(
        make_frame(date(2026, 1, 5), date(2026, 1, 6)),
        expected,
    )

    assert MarketDataQualityDiagnosticCode.TRUNCATED_START in codes
    assert MarketDataQualityDiagnosticCode.TRUNCATED_END not in codes


def test_missing_last_expected_trade_date_flags_truncated_end() -> None:
    expected = (
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    )

    codes = diagnostic_codes(
        make_frame(date(2026, 1, 2), date(2026, 1, 5)),
        expected,
    )

    assert MarketDataQualityDiagnosticCode.TRUNCATED_END in codes
    assert MarketDataQualityDiagnosticCode.TRUNCATED_START not in codes


def test_missingness_at_threshold_is_allowed() -> None:
    expected = tuple(date(2026, 1, day) for day in range(1, 11))
    frame = make_frame(*expected[1:])

    diagnostics = diagnose_price_frame_quality(
        frame,
        requested_start=date(2026, 1, 1),
        requested_end=date(2026, 1, 11),
        expected_trade_dates=expected,
    )
    codes = {diagnostic.code for diagnostic in diagnostics}

    assert MAX_MISSING_EXPECTED_OBSERVATION_RATIO == 0.10
    assert MarketDataQualityDiagnosticCode.EXCESSIVE_MISSING_OBSERVATIONS not in codes
    assert MarketDataQualityDiagnosticCode.TRUNCATED_START in codes


def test_missingness_above_threshold_is_flagged() -> None:
    expected = tuple(date(2026, 1, day) for day in range(1, 11))
    frame = make_frame(*expected[2:])

    diagnostics = diagnose_price_frame_quality(
        frame,
        requested_start=date(2026, 1, 1),
        requested_end=date(2026, 1, 11),
        expected_trade_dates=expected,
    )
    missingness = next(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.code is MarketDataQualityDiagnosticCode.EXCESSIVE_MISSING_OBSERVATIONS
    )

    assert missingness.expected_observations == 10
    assert missingness.observed_observations == 8
    assert missingness.missing_observations == 2
    assert missingness.missing_ratio == pytest.approx(0.20)


def test_diagnostics_preserve_existing_duplicate_date_rejection() -> None:
    duplicated = make_frame(date(2026, 1, 2), date(2026, 1, 2))

    with pytest.raises(MarketDataQualityError):
        diagnose_price_frame_quality(
            duplicated,
            requested_start=date(2026, 1, 1),
            requested_end=date(2026, 1, 3),
            expected_trade_dates=(date(2026, 1, 2),),
        )


def test_diagnostics_preserve_existing_ohlc_rejection() -> None:
    invalid_frame: PriceFrame = (
        PriceBar(
            asset_id=ASSET_ID,
            trade_date=date(2026, 1, 2),
            open=104.0,
            high=103.0,
            low=99.0,
            close=102.0,
            adjusted_close=101.5,
            volume=1_000_000,
            source="test",
            retrieved_at=RETRIEVED_AT,
        ),
    )

    with pytest.raises(MarketDataQualityError):
        diagnose_price_frame_quality(
            invalid_frame,
            requested_start=date(2026, 1, 1),
            requested_end=date(2026, 1, 3),
            expected_trade_dates=(date(2026, 1, 2),),
        )


def test_diagnostics_preserve_existing_out_of_order_rejection() -> None:
    out_of_order = make_frame(date(2026, 1, 5), date(2026, 1, 2))

    with pytest.raises(MarketDataQualityError):
        diagnose_price_frame_quality(
            out_of_order,
            requested_start=date(2026, 1, 1),
            requested_end=date(2026, 1, 6),
            expected_trade_dates=(
                date(2026, 1, 2),
                date(2026, 1, 5),
            ),
        )


def test_diagnostics_do_not_fill_missing_price_values() -> None:
    frame: PriceFrame = (
        PriceBar(
            asset_id=ASSET_ID,
            trade_date=date(2026, 1, 2),
            open=None,
            high=None,
            low=None,
            close=None,
            adjusted_close=None,
            volume=None,
            source="test",
            retrieved_at=RETRIEVED_AT,
        ),
    )

    diagnostics = diagnose_price_frame_quality(
        frame,
        requested_start=date(2026, 1, 1),
        requested_end=date(2026, 1, 3),
        expected_trade_dates=(date(2026, 1, 2),),
    )

    assert diagnostics == ()
    assert frame[0].open is None
    assert frame[0].close is None
    assert frame[0].adjusted_close is None
    assert frame[0].volume is None
