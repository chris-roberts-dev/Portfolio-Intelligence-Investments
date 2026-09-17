"""Canonical target-weight, drift, and simulated-notional calculations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import NoReturn
from uuid import UUID

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.rebalancing.contracts import (
    CurrentValue,
    RebalanceLine,
    RebalanceSimulationResult,
    RebalancingError,
    RebalancingErrorCode,
    SimulatedTradeDirection,
    TargetWeight,
)


def validate_target_weights(
    targets: Sequence[TargetWeight],
    *,
    tolerance: float = WEIGHT_SUM_TOLERANCE,
) -> tuple[TargetWeight, ...]:
    """Validate long-only target weights, including at most one cash target."""
    normalized_tolerance = _finite_nonnegative(tolerance, "tolerance")
    if not targets:
        _raise(
            RebalancingErrorCode.INVALID_TARGET_WEIGHTS,
            "At least one target weight is required.",
        )

    normalized: list[TargetWeight] = []
    seen: set[UUID | None] = set()

    for index, target in enumerate(targets):
        if target.asset_id in seen:
            _raise(
                RebalancingErrorCode.INVALID_TARGET_WEIGHTS,
                f"Duplicate target key at index {index}.",
            )

        seen.add(target.asset_id)
        weight = _finite(target.weight, f"targets[{index}].weight")

        if weight < 0.0 or weight > 1.0:
            _raise(
                RebalancingErrorCode.INVALID_TARGET_WEIGHTS,
                f"targets[{index}].weight must be between zero and one.",
            )

        normalized.append(
            TargetWeight(
                asset_id=target.asset_id,
                weight=weight,
            )
        )

    total = math.fsum(target.weight for target in normalized)

    if abs(total - 1.0) > normalized_tolerance:
        _raise(
            RebalancingErrorCode.INVALID_TARGET_WEIGHTS,
            "Target weights must sum to one within tolerance.",
        )

    return tuple(normalized)


def simulate_rebalance(
    current_values: Sequence[CurrentValue],
    targets: Sequence[TargetWeight],
    *,
    tolerance: float = WEIGHT_SUM_TOLERANCE,
) -> RebalanceSimulationResult:
    """Compute canonical drift and simulated trade notionals at current value ``V``."""
    normalized_targets = validate_target_weights(
        targets,
        tolerance=tolerance,
    )
    normalized_current = _validate_current_values(current_values)
    total_value = math.fsum(item.market_value for item in normalized_current)

    if total_value <= 0.0:
        _raise(
            RebalancingErrorCode.INVALID_CURRENT_VALUES,
            "Total investable portfolio value must be positive.",
        )

    current_by_key = {item.asset_id: item.market_value for item in normalized_current}
    target_by_key = {item.asset_id: item.weight for item in normalized_targets}
    ordered_keys: list[UUID | None] = [item.asset_id for item in normalized_targets]
    ordered_keys.extend(
        item.asset_id for item in normalized_current if item.asset_id not in target_by_key
    )

    lines: list[RebalanceLine] = []

    for key in ordered_keys:
        current_value = current_by_key.get(key, 0.0)
        target_weight = target_by_key.get(key, 0.0)
        current_weight = current_value / total_value
        absolute_drift = current_weight - target_weight
        relative_drift = None if target_weight == 0.0 else absolute_drift / target_weight
        target_value = total_value * target_weight
        trade_notional = target_value - current_value
        direction = _direction(
            trade_notional,
            tolerance=tolerance,
        )

        lines.append(
            RebalanceLine(
                asset_id=key,
                current_value=current_value,
                target_value=target_value,
                current_weight=current_weight,
                target_weight=target_weight,
                absolute_drift=absolute_drift,
                relative_drift=relative_drift,
                trade_notional=trade_notional,
                direction=direction,
            )
        )

    return RebalanceSimulationResult(
        total_investable_value=total_value,
        lines=tuple(lines),
        current_weight_sum=math.fsum(line.current_weight for line in lines),
        target_weight_sum=math.fsum(line.target_weight for line in lines),
    )


def _validate_current_values(
    values: Sequence[CurrentValue],
) -> tuple[CurrentValue, ...]:
    if not values:
        _raise(
            RebalancingErrorCode.INVALID_CURRENT_VALUES,
            "Current values must not be empty.",
        )

    seen: set[UUID | None] = set()
    normalized: list[CurrentValue] = []

    for index, item in enumerate(values):
        if item.asset_id in seen:
            _raise(
                RebalancingErrorCode.INVALID_CURRENT_VALUES,
                f"Duplicate current-value key at index {index}.",
            )

        seen.add(item.asset_id)
        value = _finite(
            item.market_value,
            f"current_values[{index}].market_value",
        )

        if value < 0.0:
            _raise(
                RebalancingErrorCode.INVALID_CURRENT_VALUES,
                f"current_values[{index}].market_value must not be negative.",
            )

        normalized.append(
            CurrentValue(
                asset_id=item.asset_id,
                market_value=value,
            )
        )

    return tuple(normalized)


def _direction(
    notional: float,
    *,
    tolerance: float,
) -> SimulatedTradeDirection:
    if abs(notional) <= tolerance:
        return SimulatedTradeDirection.NONE

    return SimulatedTradeDirection.BUY if notional > 0.0 else SimulatedTradeDirection.SELL


def _finite(
    value: object,
    field_name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _raise(
            RebalancingErrorCode.INVALID_INPUT,
            f"{field_name} must be a real number.",
        )

    number = float(value)

    if not math.isfinite(number):
        _raise(
            RebalancingErrorCode.INVALID_INPUT,
            f"{field_name} must be finite.",
        )

    return number


def _finite_nonnegative(
    value: object,
    field_name: str,
) -> float:
    number = _finite(value, field_name)

    if number < 0.0:
        _raise(
            RebalancingErrorCode.INVALID_INPUT,
            f"{field_name} must not be negative.",
        )

    return number


def _raise(
    code: RebalancingErrorCode,
    message: str,
) -> NoReturn:
    raise RebalancingError(
        code,
        message,
    )
