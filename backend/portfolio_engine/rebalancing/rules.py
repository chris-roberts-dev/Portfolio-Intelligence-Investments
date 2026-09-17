"""Canonical current-time schedule and drift-threshold rebalance rules."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.rebalancing.contracts import (
    RebalanceLine,
    RebalanceRuleEvaluation,
    RebalanceSchedule,
    RebalancingError,
    RebalancingErrorCode,
)


def threshold_rebalance_triggered(
    lines: Sequence[RebalanceLine],
    *,
    threshold: float,
) -> bool:
    """Return whether any absolute drift reaches the configured threshold.

    Floating-point drift values are compared using the canonical portfolio
    weight tolerance so an analytically exact threshold boundary is not missed
    because of binary floating-point representation.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise RebalancingError(
            RebalancingErrorCode.INVALID_INPUT,
            "threshold must be numeric.",
        )

    normalized = float(threshold)

    if not math.isfinite(normalized) or normalized < 0.0 or normalized > 1.0:
        raise RebalancingError(
            RebalancingErrorCode.INVALID_INPUT,
            "threshold must be finite and between zero and one.",
        )

    return any(
        abs(line.absolute_drift) >= normalized
        or math.isclose(
            abs(line.absolute_drift),
            normalized,
            rel_tol=0.0,
            abs_tol=WEIGHT_SUM_TOLERANCE,
        )
        for line in lines
    )


def scheduled_rebalance_due(
    *,
    schedule: RebalanceSchedule,
    decision_date: date,
    previous_rebalance_date: date | None,
) -> bool:
    """Return true on the first evaluated date in a new configured calendar period."""
    if previous_rebalance_date is None:
        return True

    if previous_rebalance_date > decision_date:
        raise RebalancingError(
            RebalancingErrorCode.INVALID_INPUT,
            "previous_rebalance_date must not be after decision_date.",
        )

    return _period_key(
        previous_rebalance_date,
        schedule,
    ) != _period_key(
        decision_date,
        schedule,
    )


def evaluate_rebalance_rules(
    lines: Sequence[RebalanceLine],
    *,
    decision_date: date,
    threshold: float | None = None,
    schedule: RebalanceSchedule | None = None,
    previous_rebalance_date: date | None = None,
) -> RebalanceRuleEvaluation:
    """Evaluate optional threshold/schedule policies without executing trades."""
    threshold_triggered = (
        None
        if threshold is None
        else threshold_rebalance_triggered(
            lines,
            threshold=threshold,
        )
    )

    schedule_due = (
        None
        if schedule is None
        else scheduled_rebalance_due(
            schedule=schedule,
            decision_date=decision_date,
            previous_rebalance_date=previous_rebalance_date,
        )
    )

    return RebalanceRuleEvaluation(
        threshold=threshold,
        threshold_triggered=threshold_triggered,
        schedule=schedule,
        previous_rebalance_date=previous_rebalance_date,
        decision_date=decision_date,
        schedule_due=schedule_due,
    )


def _period_key(
    value: date,
    schedule: RebalanceSchedule,
) -> tuple[int, int]:
    if schedule is RebalanceSchedule.MONTHLY:
        return (value.year, value.month)

    if schedule is RebalanceSchedule.QUARTERLY:
        return (
            value.year,
            ((value.month - 1) // 3) + 1,
        )

    return (value.year, 1)
