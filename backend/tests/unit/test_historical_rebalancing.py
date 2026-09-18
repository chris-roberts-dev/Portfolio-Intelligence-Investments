from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from portfolio_engine.contracts.market_data import PriceBar
from portfolio_engine.rebalancing import (
    HistoricalPosition,
    HistoricalRebalancePolicy,
    RebalanceSchedule,
    TargetWeight,
    compare_historical_rebalancing,
)

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")
RETRIEVED_AT = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _bar(asset_id: UUID, trade_date: date, adjusted_close: float) -> PriceBar:
    return PriceBar(
        asset_id=asset_id,
        trade_date=trade_date,
        open=adjusted_close,
        high=adjusted_close,
        low=adjusted_close,
        close=adjusted_close,
        adjusted_close=adjusted_close,
        volume=100,
        source="mock",
        retrieved_at=RETRIEVED_AT,
    )


def test_annual_rebalance_executes_next_observation_with_manual_state_fixture() -> None:
    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    d3 = date(2026, 1, 6)
    result = compare_historical_rebalancing(
        price_frames={
            A: (_bar(A, d1, 10.0), _bar(A, d2, 20.0), _bar(A, d3, 20.0)),
            B: (_bar(B, d1, 10.0), _bar(B, d2, 10.0), _bar(B, d3, 10.0)),
        },
        initial_positions=(HistoricalPosition(A, 10.0),),
        initial_cash=0.0,
        targets=(TargetWeight(A, 0.5), TargetWeight(B, 0.5)),
        policies=(HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),),
    )

    policy = result.policy_results[0]
    event = policy.events[0]
    assert event.decision_date == d1
    assert event.execution_date == d2
    assert event.pre_trade_value == pytest.approx(200.0)
    assert event.post_trade_value == pytest.approx(200.0)
    assert event.turnover == pytest.approx(1.0)
    assert event.commission_cost == pytest.approx(0.0)
    assert event.slippage_cost == pytest.approx(0.0)
    assert policy.trade_count == 2
    assert policy.rebalance_count == 1
    assert policy.ending_value == pytest.approx(200.0)
    assert policy.cumulative_return == pytest.approx(1.0)

    sell, buy = event.trades
    assert sell.asset_id == A
    assert sell.quantity == pytest.approx(5.0)
    assert sell.fill_notional == pytest.approx(100.0)
    assert buy.asset_id == B
    assert buy.quantity == pytest.approx(10.0)
    assert buy.fill_notional == pytest.approx(100.0)
    assert policy.snapshots[1].cash_value == pytest.approx(0.0)


def test_future_price_change_cannot_change_threshold_decision_at_t() -> None:
    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    base_kwargs = {
        "initial_positions": (HistoricalPosition(A, 6.0), HistoricalPosition(B, 4.0)),
        "initial_cash": 0.0,
        "targets": (TargetWeight(A, 0.5), TargetWeight(B, 0.5)),
        "policies": (HistoricalRebalancePolicy("threshold", threshold=0.1),),
    }
    first = compare_historical_rebalancing(
        price_frames={
            A: (_bar(A, d1, 10.0), _bar(A, d2, 10.0)),
            B: (_bar(B, d1, 10.0), _bar(B, d2, 10.0)),
        },
        **base_kwargs,
    )
    changed_future = compare_historical_rebalancing(
        price_frames={
            A: (_bar(A, d1, 10.0), _bar(A, d2, 100.0)),
            B: (_bar(B, d1, 10.0), _bar(B, d2, 1.0)),
        },
        **base_kwargs,
    )

    first_event = first.policy_results[0].events[0]
    changed_event = changed_future.policy_results[0].events[0]
    assert first_event.decision_date == changed_event.decision_date == d1
    assert first_event.execution_date == changed_event.execution_date == d2
    assert first_event.decision_lines == changed_event.decision_lines


def test_costed_buy_is_scaled_to_preserve_nonnegative_cash() -> None:
    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    result = compare_historical_rebalancing(
        price_frames={A: (_bar(A, d1, 10.0), _bar(A, d2, 10.0))},
        initial_positions=(),
        initial_cash=100.0,
        targets=(TargetWeight(A, 1.0),),
        policies=(HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),),
        commission_rate=0.01,
        slippage_rate=0.01,
    )

    policy = result.policy_results[0]
    event = policy.events[0]
    assert policy.snapshots[-1].cash_value == pytest.approx(0.0, abs=1e-10)
    assert event.trades[0].quantity < 10.0
    assert event.commission_cost > 0.0
    assert event.slippage_cost > 0.0
    assert event.post_trade_value < event.pre_trade_value
    assert policy.total_cost == pytest.approx(event.commission_cost + event.slippage_cost)


def test_manual_sell_fixture_proves_cash_turnover_commission_and_value_effect() -> None:
    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    result = compare_historical_rebalancing(
        price_frames={A: (_bar(A, d1, 10.0), _bar(A, d2, 10.0))},
        initial_positions=(HistoricalPosition(A, 10.0),),
        initial_cash=0.0,
        targets=(TargetWeight(A, 0.5), TargetWeight(None, 0.5)),
        policies=(HistoricalRebalancePolicy("annual", schedule=RebalanceSchedule.ANNUAL),),
        commission_rate=0.01,
        slippage_rate=0.0,
    )

    policy = result.policy_results[0]
    event = policy.events[0]
    trade = event.trades[0]
    assert trade.direction.value == "SELL"
    assert trade.quantity == pytest.approx(5.0)
    assert trade.fill_notional == pytest.approx(50.0)
    assert trade.commission_cost == pytest.approx(0.5)
    assert event.turnover == pytest.approx(0.5)
    assert policy.snapshots[-1].cash_value == pytest.approx(49.5)
    assert event.post_trade_value == pytest.approx(99.5)
    assert policy.ending_value == pytest.approx(99.5)
    assert policy.total_cost == pytest.approx(0.5)


def test_identical_inputs_replay_to_identical_historical_result() -> None:
    d1 = date(2026, 1, 2)
    d2 = date(2026, 1, 5)
    kwargs = {
        "price_frames": {
            A: (_bar(A, d1, 10.0), _bar(A, d2, 11.0)),
            B: (_bar(B, d1, 20.0), _bar(B, d2, 19.0)),
        },
        "initial_positions": (HistoricalPosition(A, 5.0), HistoricalPosition(B, 2.5)),
        "initial_cash": 0.0,
        "targets": (TargetWeight(A, 0.5), TargetWeight(B, 0.5)),
        "policies": (
            HistoricalRebalancePolicy("quarterly", schedule=RebalanceSchedule.QUARTERLY),
            HistoricalRebalancePolicy("threshold", threshold=0.05),
        ),
        "commission_rate": 0.001,
        "slippage_rate": 0.002,
    }
    assert compare_historical_rebalancing(**kwargs) == compare_historical_rebalancing(**kwargs)
