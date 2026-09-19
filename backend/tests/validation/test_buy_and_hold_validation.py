from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from portfolio_engine.backtesting import BacktestDataProvenance, run_backtest
from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.strategies import BuyAndHoldStrategy, BuyAndHoldTargetWeight

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
D1 = date(2026, 1, 2)
D2 = date(2026, 1, 5)
D3 = date(2026, 1, 6)
D4 = date(2026, 1, 7)
RETRIEVED_AT = datetime(2026, 1, 6, 22, 0, tzinfo=UTC)
PROVENANCE = BacktestDataProvenance(provider="mock", retrieved_at=RETRIEVED_AT)


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


def test_buy_and_hold_uses_complete_case_dates_without_forward_fill() -> None:
    result = run_backtest(
        price_frames={
            A: (_bar(A, D1, 10.0), _bar(A, D2, 11.0), _bar(A, D3, 12.0)),
            B: (_bar(B, D1, 20.0), _bar(B, D2, None), _bar(B, D3, 24.0)),
        },
        initial_positions=(),
        initial_cash=100.0,
        strategy=BuyAndHoldStrategy(
            targets=(
                BuyAndHoldTargetWeight(A, 0.5),
                BuyAndHoldTargetWeight(B, 0.5),
            )
        ),
        requested_period_start=D1,
        requested_period_end_exclusive=D4,
        data_provenance=PROVENANCE,
    )

    assert result.aligned_dates == (D1, D3)
    assert result.decisions[0].decision_date == D1
    assert result.executions[0].execution_date == D3
    assert result.warnings[0].code.value == "INCOMPLETE_DATE_INTERSECTION"
    assert "without forward-filling or zero substitution" in result.warnings[0].message
