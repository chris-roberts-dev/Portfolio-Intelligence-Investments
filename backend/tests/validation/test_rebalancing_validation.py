from uuid import UUID

import pytest

from portfolio_engine.rebalancing import (
    CurrentValue,
    RebalancingError,
    TargetWeight,
    simulate_rebalance,
)

A = UUID("00000000-0000-0000-0000-000000000001")


def test_target_weights_must_sum_to_one() -> None:
    with pytest.raises(RebalancingError):
        simulate_rebalance((CurrentValue(A, 100.0),), (TargetWeight(A, 0.9),))


def test_nonfinite_values_fail() -> None:
    with pytest.raises(RebalancingError):
        simulate_rebalance((CurrentValue(A, float("nan")),), (TargetWeight(A, 1.0),))
