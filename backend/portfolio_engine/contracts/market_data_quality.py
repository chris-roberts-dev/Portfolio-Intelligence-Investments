"""Framework-independent market-data coverage and missingness diagnostics.

The canonical price-frame validator remains authoritative for row-level
correctness. This module adds request-window diagnostics using an explicit
expected trading-date schedule supplied by the caller, so weekends and other
non-trading days are never inferred to be missing observations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from portfolio_engine.config import MAX_MISSING_EXPECTED_OBSERVATION_RATIO
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.contracts.market_data_validation import validate_price_frame


class MarketDataQualityDiagnosticCode(StrEnum):
    """Stable codes for non-destructive market-data quality diagnostics."""

    TRUNCATED_START = "TRUNCATED_START"
    TRUNCATED_END = "TRUNCATED_END"
    EXCESSIVE_MISSING_OBSERVATIONS = "EXCESSIVE_MISSING_OBSERVATIONS"


@dataclass(frozen=True, slots=True)
class MarketDataQualityDiagnostic:
    """One deterministic data-quality diagnostic for a requested period."""

    code: MarketDataQualityDiagnosticCode
    message: str
    expected_observations: int
    observed_observations: int
    missing_observations: int
    missing_ratio: float


def diagnose_price_frame_quality(
    frame: PriceFrame,
    *,
    requested_start: date,
    requested_end: date,
    expected_trade_dates: Sequence[date],
    max_missing_ratio: float = MAX_MISSING_EXPECTED_OBSERVATION_RATIO,
) -> tuple[MarketDataQualityDiagnostic, ...]:
    """Validate a canonical frame and diagnose request-period data gaps.

    ``requested_start`` is inclusive and ``requested_end`` is exclusive.

    The caller supplies the expected trading dates. This function does not
    invent a trading calendar, assume weekdays are sessions, or classify
    weekends/holidays as missing observations. Missingness is measured only
    against the explicitly supplied expected trading-date schedule.
    """
    validate_price_frame(frame)
    _validate_diagnostic_inputs(
        requested_start=requested_start,
        requested_end=requested_end,
        expected_trade_dates=expected_trade_dates,
        max_missing_ratio=max_missing_ratio,
    )

    expected_dates = tuple(expected_trade_dates)

    if not expected_dates:
        return ()

    observed_dates = {
        bar.trade_date for bar in frame if requested_start <= bar.trade_date < requested_end
    }
    observed_expected_dates = tuple(
        trade_date for trade_date in expected_dates if trade_date in observed_dates
    )
    missing_dates = tuple(
        trade_date for trade_date in expected_dates if trade_date not in observed_dates
    )

    expected_count = len(expected_dates)
    observed_count = len(observed_expected_dates)
    missing_count = len(missing_dates)
    missing_ratio = missing_count / expected_count

    diagnostics: list[MarketDataQualityDiagnostic] = []

    if expected_dates[0] not in observed_dates:
        diagnostics.append(
            MarketDataQualityDiagnostic(
                code=MarketDataQualityDiagnosticCode.TRUNCATED_START,
                message=(
                    "Observed coverage starts after the first expected trading "
                    "date in the requested period."
                ),
                expected_observations=expected_count,
                observed_observations=observed_count,
                missing_observations=missing_count,
                missing_ratio=missing_ratio,
            )
        )

    if expected_dates[-1] not in observed_dates:
        diagnostics.append(
            MarketDataQualityDiagnostic(
                code=MarketDataQualityDiagnosticCode.TRUNCATED_END,
                message=(
                    "Observed coverage ends before the last expected trading "
                    "date in the requested period."
                ),
                expected_observations=expected_count,
                observed_observations=observed_count,
                missing_observations=missing_count,
                missing_ratio=missing_ratio,
            )
        )

    if missing_ratio > max_missing_ratio:
        diagnostics.append(
            MarketDataQualityDiagnostic(
                code=MarketDataQualityDiagnosticCode.EXCESSIVE_MISSING_OBSERVATIONS,
                message=(
                    "Missing expected trading-date observations exceed the "
                    "configured maximum ratio."
                ),
                expected_observations=expected_count,
                observed_observations=observed_count,
                missing_observations=missing_count,
                missing_ratio=missing_ratio,
            )
        )

    return tuple(diagnostics)


def _validate_diagnostic_inputs(
    *,
    requested_start: date,
    requested_end: date,
    expected_trade_dates: Sequence[date],
    max_missing_ratio: float,
) -> None:
    if requested_start >= requested_end:
        raise ValueError("requested_start must be earlier than requested_end")

    if not 0.0 <= max_missing_ratio <= 1.0:
        raise ValueError("max_missing_ratio must be between 0 and 1 inclusive")

    expected_dates = tuple(expected_trade_dates)

    if expected_dates != tuple(sorted(set(expected_dates))):
        raise ValueError("expected_trade_dates must be unique and ascending")

    if any(
        trade_date < requested_start or trade_date >= requested_end for trade_date in expected_dates
    ):
        raise ValueError("expected_trade_dates must fall within the requested period")
