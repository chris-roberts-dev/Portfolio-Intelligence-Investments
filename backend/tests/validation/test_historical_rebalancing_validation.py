from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.rebalancing import (
    HistoricalRebalancePolicy,
    RebalanceSchedule,
    RebalancingError,
    RebalancingErrorCode,
    TargetWeight,
    compare_historical_rebalancing,
)

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
RETRIEVED_AT = datetime(2026, 1, 6, 22, 0, tzinfo=UTC)


def _bar(asset_id: UUID, trade_date: date, price: float | None) -> PriceBar:
    return PriceBar(
        asset_id=asset_id,
        trade_date=trade_date,
        open=price,
        high=price,
        low=price,
        close=price,
        adjusted_close=price,
        volume=100,
        source="mock",
        retrieved_at=RETRIEVED_AT,
    )


def test_missing_required_asset_history_fails_explicitly() -> None:
    with pytest.raises(RebalancingError) as exc_info:
        compare_historical_rebalancing(
            price_frames={
                A: (
                    _bar(A, date(2026, 1, 2), 10.0),
                    _bar(A, date(2026, 1, 5), 10.0),
                )
            },
            initial_positions=(),
            initial_cash=100.0,
            targets=(TargetWeight(A, 0.5), TargetWeight(B, 0.5)),
            policies=(HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),),
        )
    assert exc_info.value.code is RebalancingErrorCode.INVALID_PRICE_HISTORY


def test_complete_case_alignment_warns_without_forward_fill() -> None:
    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    d3 = date(2026, 1, 6)
    result = compare_historical_rebalancing(
        price_frames={
            A: (_bar(A, d1, 10.0), _bar(A, d2, 10.0), _bar(A, d3, 10.0)),
            B: (_bar(B, d1, 10.0), _bar(B, d3, 10.0)),
        },
        initial_positions=(),
        initial_cash=100.0,
        targets=(TargetWeight(A, 0.5), TargetWeight(B, 0.5)),
        policies=(HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),),
    )
    assert result.aligned_dates == (d1, d3)
    assert result.warnings
    assert "without forward-filling" in result.warnings[0].message
