"""Unit tests for canonical historical optimization estimators."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import numpy as np
import pytest

from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.optimization import OptimizationError, OptimizationErrorCode
from portfolio_engine.optimization.estimators import estimate_historical_inputs

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
RETRIEVED = datetime(2026, 1, 10, tzinfo=UTC)


def _frame(asset_id: UUID, closes: list[float | None]) -> tuple[PriceBar, ...]:
    start = date(2026, 1, 1)
    return tuple(
        PriceBar(
            asset_id=asset_id,
            trade_date=start + timedelta(days=index),
            open=value,
            high=value,
            low=value,
            close=value,
            adjusted_close=value,
            volume=100,
            source="fixture",
            retrieved_at=RETRIEVED,
        )
        for index, value in enumerate(closes)
    )


def test_estimators_use_complete_case_adjusted_close_returns() -> None:
    frames = {
        str(A): _frame(A, [100.0, 110.0, 121.0, 133.1]),
        str(B): _frame(B, [100.0, 105.0, 110.25, 115.7625]),
    }

    result = estimate_historical_inputs((str(A), str(B)), frames)

    assert result.observations == 3
    assert result.expected_returns == pytest.approx((25.2, 12.6))
    assert np.asarray(result.covariance) == pytest.approx(np.zeros((2, 2)), abs=1e-12)


def test_estimators_drop_dates_missing_adjusted_close_before_returns() -> None:
    frames = {
        str(A): _frame(A, [100.0, 101.0, 102.0, 103.0, 104.0]),
        str(B): _frame(B, [50.0, 51.0, None, 53.0, 54.0]),
    }

    result = estimate_historical_inputs((str(A), str(B)), frames)

    assert result.observations == 3
    assert len(result.return_dates) == 3


def test_estimators_require_enough_complete_case_prices() -> None:
    frames = {
        str(A): _frame(A, [100.0, 101.0]),
        str(B): _frame(B, [50.0, 51.0]),
    }

    with pytest.raises(OptimizationError) as exc_info:
        estimate_historical_inputs((str(A), str(B)), frames)

    assert exc_info.value.code is OptimizationErrorCode.INSUFFICIENT_DATA
