"""Persisted owner-scoped Phase 6 backtest run resources.

Development guide references: Sections 15.2-15.3, 17.2, 20.2, and 23.7.
"""

from __future__ import annotations

import math
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from portfolio_engine.backtesting import BACKTEST_METHOD_VERSION
from portfolio_engine.strategies import BUY_AND_HOLD_STRATEGY_VERSION
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


class BacktestRunStatus(models.TextChoices):
    """Canonical persisted backtest run states."""

    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class BacktestStrategyName(models.TextChoices):
    """Strategies currently exposed by the Phase 6 backend contract."""

    BUY_AND_HOLD = "BUY_AND_HOLD", "Buy and hold"


class BacktestRun(models.Model):
    """Immutable-input, auditable historical backtest owned by one user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backtest_runs",
    )
    status = models.CharField(
        max_length=16,
        choices=BacktestRunStatus.choices,
        default=BacktestRunStatus.PENDING,
    )
    strategy = models.CharField(
        max_length=32,
        choices=BacktestStrategyName.choices,
        default=BacktestStrategyName.BUY_AND_HOLD,
    )
    period_start = models.DateField()
    period_end_exclusive = models.DateField()
    provider = models.CharField(max_length=32)
    price_field = models.CharField(max_length=32, default="adjusted_close")
    included_asset_ids = models.JSONField(default=list)
    parameters = models.JSONField(default=dict)
    initial_cash = models.DecimalField(max_digits=24, decimal_places=8)
    commission_rate = models.DecimalField(
        max_digits=18,
        decimal_places=12,
        default=Decimal("0"),
    )
    slippage_rate = models.DecimalField(
        max_digits=18,
        decimal_places=12,
        default=Decimal("0"),
    )
    result = models.JSONField(null=True, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    engine_version = models.CharField(max_length=64, default=PORTFOLIO_ENGINE_VERSION)
    method_version = models.CharField(max_length=32, default=BACKTEST_METHOD_VERSION)
    strategy_version = models.CharField(
        max_length=32,
        default=BUY_AND_HOLD_STRATEGY_VERSION,
    )
    data_retrieved_at = models.DateTimeField(null=True, blank=True)
    data_fingerprint = models.CharField(max_length=64, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return f"{self.strategy} {self.id} ({self.status})"

    def clean(self) -> None:
        """Reject inconsistent, non-finite, or non-reproducible persisted state."""
        super().clean()
        errors: dict[str, str] = {}

        if self.period_end_exclusive <= self.period_start:
            errors["period_end_exclusive"] = "period_end_exclusive must be later than period_start."
        if not self.provider.strip():
            errors["provider"] = "provider must not be blank."
        if self.price_field != "adjusted_close":
            errors["price_field"] = "Backtest runs must use adjusted_close."
        if self.initial_cash <= Decimal("0"):
            errors["initial_cash"] = "initial_cash must be positive."
        if self.commission_rate < Decimal("0") or self.commission_rate > Decimal("1"):
            errors["commission_rate"] = "commission_rate must be between zero and one."
        if self.slippage_rate < Decimal("0") or self.slippage_rate > Decimal("1"):
            errors["slippage_rate"] = "slippage_rate must be between zero and one."
        if not self.engine_version.strip():
            errors["engine_version"] = "engine_version must not be blank."
        if not self.method_version.strip():
            errors["method_version"] = "method_version must not be blank."
        if not self.strategy_version.strip():
            errors["strategy_version"] = "strategy_version must not be blank."
        if not isinstance(self.included_asset_ids, list) or not self.included_asset_ids:
            errors["included_asset_ids"] = "Backtest runs require included assets."

        status = BacktestRunStatus(self.status)
        if status in (BacktestRunStatus.PENDING, BacktestRunStatus.RUNNING):
            if self.result is not None:
                errors["result"] = "Pending/running backtests cannot have a result."
            if self.failure_code or self.failure_message:
                errors["failure_code"] = "Pending/running backtests cannot have failure metadata."
        elif status == BacktestRunStatus.SUCCEEDED:
            if self.result is None:
                errors["result"] = "Successful backtests require a result."
            if self.failure_code or self.failure_message:
                errors["failure_code"] = "Successful backtests cannot have failure metadata."
            if self.completed_at is None:
                errors["completed_at"] = "Successful backtests require completed_at."
        elif status == BacktestRunStatus.FAILED:
            if self.result is not None:
                errors["result"] = "Failed backtests cannot have a successful result."
            if not self.failure_code.strip() or not self.failure_message.strip():
                errors["failure_code"] = "Failed backtests require a code and message."
            if self.completed_at is None:
                errors["completed_at"] = "Failed backtests require completed_at."

        try:
            _validate_json_finite(self.included_asset_ids)
            _validate_json_finite(self.parameters)
            _validate_json_finite(self.result)
            _validate_json_finite(self.warnings)
        except ValueError as exc:
            errors["result"] = str(exc)

        if errors:
            raise ValidationError(errors)


def _validate_json_finite(value: Any) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Persisted backtest JSON cannot contain NaN or infinity.")
        return
    if isinstance(value, dict):
        for child in value.values():
            _validate_json_finite(child)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _validate_json_finite(child)
