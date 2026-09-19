from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.backtesting import (
    BacktestDataProvenance,
    BacktestError,
    BacktestErrorCode,
    OrderIntent,
    StrategyContext,
    run_backtest,
)
from portfolio_engine.contracts.market_data import PriceBar

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
D4 = date(2026, 1, 7)
RETRIEVED_AT = datetime(2026, 1, 7, 22, 0, tzinfo=UTC)
PROVENANCE = BacktestDataProvenance(provider="mock", retrieved_at=RETRIEVED_AT)


@dataclass
class NoOpStrategy:
    name: str = "noop"
    version: str = "1.0"
    minimum_history_observations: int = 1

    def generate_orders(self, context: StrategyContext) -> tuple[OrderIntent, ...]:
        return ()


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


def test_complete_case_alignment_excludes_missing_date_without_forward_fill_or_zero() -> None:
    result = run_backtest(
        price_frames={
            A: (_bar(A, D1, 10.0), _bar(A, D2, 11.0), _bar(A, D3, 12.0)),
            B: (_bar(B, D1, 20.0), _bar(B, D2, None), _bar(B, D3, 21.0)),
        },
        initial_positions=(),
        initial_cash=100.0,
        strategy=NoOpStrategy(),
        requested_period_start=D1,
        requested_period_end_exclusive=D4,
        data_provenance=PROVENANCE,
    )

    assert result.aligned_dates == (D1, D3)
    assert tuple(point.trade_date for point in result.equity_curve) == (D1, D3)
    assert result.warnings
    assert result.warnings[0].code.value == "INCOMPLETE_DATE_INTERSECTION"
    assert "without forward-filling or zero substitution" in result.warnings[0].message


def test_nonpositive_adjusted_close_fails_instead_of_becoming_zero_return() -> None:
    with pytest.raises(BacktestError) as exc_info:
        run_backtest(
            price_frames={A: (_bar(A, D1, 10.0), _bar(A, D2, 0.0))},
            initial_positions=(),
            initial_cash=100.0,
            strategy=NoOpStrategy(),
            requested_period_start=D1,
            requested_period_end_exclusive=D3,
            data_provenance=PROVENANCE,
        )

    assert exc_info.value.code is BacktestErrorCode.INVALID_PRICE_HISTORY
    assert "positive" in str(exc_info.value)


def test_insufficient_complete_case_history_fails_explicitly() -> None:
    with pytest.raises(BacktestError) as exc_info:
        run_backtest(
            price_frames={
                A: (_bar(A, D1, 10.0), _bar(A, D2, 11.0)),
                B: (_bar(B, D1, 20.0), _bar(B, D3, 21.0)),
            },
            initial_positions=(),
            initial_cash=100.0,
            strategy=NoOpStrategy(),
            requested_period_start=D1,
            requested_period_end_exclusive=D4,
            data_provenance=PROVENANCE,
        )

    assert exc_info.value.code is BacktestErrorCode.INSUFFICIENT_HISTORY
