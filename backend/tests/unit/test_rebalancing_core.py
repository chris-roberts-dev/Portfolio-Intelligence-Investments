from __future__ import annotations

from uuid import UUID

import pytest

from portfolio_engine.rebalancing import CurrentValue, TargetWeight, simulate_rebalance

AAPL = UUID("00000000-0000-0000-0000-000000000001")
MSFT = UUID("00000000-0000-0000-0000-000000000002")


def test_simulated_rebalance_calculates_drift_and_notional() -> None:
    result = simulate_rebalance(
        (
            CurrentValue(AAPL, 600.0),
            CurrentValue(MSFT, 300.0),
            CurrentValue(None, 100.0),
        ),
        (
            TargetWeight(AAPL, 0.5),
            TargetWeight(MSFT, 0.4),
            TargetWeight(None, 0.1),
        ),
    )
    aapl, msft, cash = result.lines
    assert result.total_investable_value == pytest.approx(1000.0)
    assert aapl.absolute_drift == pytest.approx(0.1)
    assert aapl.trade_notional == pytest.approx(-100.0)
    assert msft.trade_notional == pytest.approx(100.0)
    assert cash.trade_notional == pytest.approx(0.0)


def test_zero_target_relative_drift_is_explicitly_undefined() -> None:
    result = simulate_rebalance(
        (CurrentValue(AAPL, 100.0),),
        (TargetWeight(None, 1.0),),
    )
    line = next(item for item in result.lines if item.asset_id == AAPL)
    assert line.target_weight == 0.0
    assert line.relative_drift is None
    assert line.trade_notional == pytest.approx(-100.0)
