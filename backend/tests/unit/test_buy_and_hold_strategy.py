from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.backtesting import BacktestDataProvenance, BacktestError, run_backtest
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


def _bar(asset_id: UUID, trade_date: date, price: float) -> PriceBar:
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


def test_buy_and_hold_manual_fixture_proves_lag_cash_costs_equity_and_returns() -> None:
    result = run_backtest(
        price_frames={
            A: (
                _bar(A, D1, 10.0),
                _bar(A, D2, 10.0),
                _bar(A, D3, 12.0),
            )
        },
        initial_positions=(),
        initial_cash=100.0,
        strategy=BuyAndHoldStrategy(targets=(BuyAndHoldTargetWeight(A, 1.0),)),
        requested_period_start=D1,
        requested_period_end_exclusive=D4,
        data_provenance=PROVENANCE,
        commission_rate=0.01,
        slippage_rate=0.0,
    )

    expected_scale = 100.0 / 101.0
    expected_quantity = 10.0 * expected_scale
    expected_notional = expected_quantity * 10.0
    expected_commission = expected_notional * 0.01
    expected_d2_value = expected_quantity * 10.0
    expected_d3_value = expected_quantity * 12.0

    assert len(result.decisions) == 1
    assert result.decisions[0].decision_date == D1
    assert result.decisions[0].orders[0].quantity == pytest.approx(10.0)

    assert len(result.executions) == 1
    execution = result.executions[0]
    assert execution.decision_date == D1
    assert execution.execution_date == D2
    assert execution.buy_scale == pytest.approx(expected_scale)
    assert execution.fills[0].quantity == pytest.approx(expected_quantity)
    assert execution.fills[0].fill_notional == pytest.approx(expected_notional)
    assert execution.commission_cost == pytest.approx(expected_commission)
    assert execution.slippage_cost == pytest.approx(0.0)
    assert execution.turnover == pytest.approx(expected_notional / 100.0)

    assert result.snapshots[0].cash == pytest.approx(100.0)
    assert result.snapshots[1].cash == pytest.approx(0.0, abs=1e-10)
    assert result.snapshots[1].positions[0].quantity == pytest.approx(expected_quantity)
    assert tuple(point.portfolio_value for point in result.equity_curve) == pytest.approx(
        (100.0, expected_d2_value, expected_d3_value)
    )
    assert tuple(point.simple_return for point in result.returns) == pytest.approx(
        (expected_d2_value / 100.0 - 1.0, 0.2)
    )
    assert result.ending_value == pytest.approx(expected_d3_value)
    assert result.cumulative_return == pytest.approx(expected_d3_value / 100.0 - 1.0)
    assert result.total_cost == pytest.approx(expected_commission)


def test_future_execution_price_change_cannot_change_initial_buy_decision() -> None:
    strategy = BuyAndHoldStrategy(
        targets=(
            BuyAndHoldTargetWeight(A, 0.5),
            BuyAndHoldTargetWeight(B, 0.5),
        )
    )
    kwargs = {
        "initial_positions": (),
        "initial_cash": 100.0,
        "strategy": strategy,
        "requested_period_start": D1,
        "requested_period_end_exclusive": D3,
        "data_provenance": PROVENANCE,
    }
    first = run_backtest(
        price_frames={
            A: (_bar(A, D1, 10.0), _bar(A, D2, 10.0)),
            B: (_bar(B, D1, 20.0), _bar(B, D2, 20.0)),
        },
        **kwargs,
    )
    changed_future = run_backtest(
        price_frames={
            A: (_bar(A, D1, 10.0), _bar(A, D2, 100.0)),
            B: (_bar(B, D1, 20.0), _bar(B, D2, 1.0)),
        },
        **kwargs,
    )

    assert first.decisions[0] == changed_future.decisions[0]
    assert first.decisions[0].decision_date == D1
    quantities = {order.asset_id: order.quantity for order in first.decisions[0].orders}
    assert quantities[A] == pytest.approx(5.0)
    assert quantities[B] == pytest.approx(2.5)
    assert first.executions[0].execution_date == D2
    assert changed_future.executions[0].execution_date == D2


def test_buy_and_hold_rejects_invalid_target_weights() -> None:
    with pytest.raises(BacktestError, match="sum to one"):
        BuyAndHoldStrategy(
            targets=(
                BuyAndHoldTargetWeight(A, 0.4),
                BuyAndHoldTargetWeight(B, 0.4),
            )
        )
