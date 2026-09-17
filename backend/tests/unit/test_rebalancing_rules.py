from datetime import date
from uuid import UUID

from portfolio_engine.rebalancing import (
    CurrentValue,
    RebalanceSchedule,
    TargetWeight,
    scheduled_rebalance_due,
    simulate_rebalance,
    threshold_rebalance_triggered,
)

AAPL = UUID("00000000-0000-0000-0000-000000000001")


def test_threshold_trigger_is_inclusive() -> None:
    result = simulate_rebalance(
        (CurrentValue(AAPL, 60.0), CurrentValue(None, 40.0)),
        (TargetWeight(AAPL, 0.5), TargetWeight(None, 0.5)),
    )
    assert threshold_rebalance_triggered(result.lines, threshold=0.1) is True


def test_schedule_period_boundaries() -> None:
    assert scheduled_rebalance_due(
        schedule=RebalanceSchedule.MONTHLY,
        previous_rebalance_date=date(2026, 8, 31),
        decision_date=date(2026, 9, 1),
    )
    assert not scheduled_rebalance_due(
        schedule=RebalanceSchedule.QUARTERLY,
        previous_rebalance_date=date(2026, 7, 1),
        decision_date=date(2026, 9, 30),
    )
    assert scheduled_rebalance_due(
        schedule=RebalanceSchedule.ANNUAL,
        previous_rebalance_date=date(2025, 12, 31),
        decision_date=date(2026, 1, 2),
    )
