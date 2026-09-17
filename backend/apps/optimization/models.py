"""Persisted Phase 5 optimization-run resources.

Development guide references: Sections 12, 15.6, and 17.2.
"""

from __future__ import annotations

import math
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


class OptimizationRunStatus(models.TextChoices):
    """Canonical persisted run states from development-guide Section 15.6."""

    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCEEDED = "SUCCEEDED", "Succeeded"
    FAILED = "FAILED", "Failed"


class OptimizationRunMethod(models.TextChoices):
    """Persisted Phase 5 optimization method identity."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT", "Equal weight"
    MINIMUM_VARIANCE = "MINIMUM_VARIANCE", "Minimum variance"
    MAXIMUM_SHARPE = "MAXIMUM_SHARPE", "Maximum Sharpe"
    EFFICIENT_FRONTIER = "EFFICIENT_FRONTIER", "Efficient frontier"


class OptimizationRunSource(models.TextChoices):
    """Explicit analytical source for one persisted optimization run."""

    PORTFOLIO = "PORTFOLIO", "Portfolio"
    AD_HOC = "AD_HOC", "Ad hoc"


class OptimizationRun(models.Model):
    """Auditable optimization run for either an owned portfolio or ad hoc universe."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="optimization_runs",
    )
    source_type = models.CharField(
        max_length=16,
        choices=OptimizationRunSource.choices,
        default=OptimizationRunSource.PORTFOLIO,
    )
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="optimization_runs",
    )
    benchmark_asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="benchmark_optimization_runs",
    )
    status = models.CharField(
        max_length=16,
        choices=OptimizationRunStatus.choices,
        default=OptimizationRunStatus.PENDING,
    )
    method = models.CharField(max_length=32, choices=OptimizationRunMethod.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    provider = models.CharField(max_length=32)
    price_field = models.CharField(max_length=32, default="adjusted_close")
    annualization_factor = models.PositiveSmallIntegerField(default=252)
    risk_free_rate_annual = models.DecimalField(
        max_digits=18,
        decimal_places=12,
        default=Decimal("0"),
    )
    included_asset_ids = models.JSONField(default=list)
    baseline_weights = models.JSONField(default=list, blank=True)
    parameters = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    engine_version = models.CharField(max_length=64, default=PORTFOLIO_ENGINE_VERSION)
    method_version = models.CharField(max_length=32, default="1.0")
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
        return f"{self.source_type}:{self.method} {self.id} ({self.status})"

    def clean(self) -> None:
        """Reject internally inconsistent or non-finite persisted run state."""
        super().clean()
        errors: dict[str, str] = {}

        if self.period_end <= self.period_start:
            errors["period_end"] = "period_end must be later than period_start."
        if not self.provider.strip():
            errors["provider"] = "provider must not be blank."
        if self.price_field != "adjusted_close":
            errors["price_field"] = "Optimization runs must use adjusted_close."
        if not self.engine_version.strip():
            errors["engine_version"] = "engine_version must not be blank."
        if not self.method_version.strip():
            errors["method_version"] = "method_version must not be blank."

        source_type = OptimizationRunSource(self.source_type)
        if source_type is OptimizationRunSource.PORTFOLIO:
            portfolio = self.portfolio
            if portfolio is None:
                errors["portfolio"] = "Portfolio-scoped runs require a portfolio."
            elif self.user_id and portfolio.user_id != self.user_id:
                errors["portfolio"] = "portfolio must belong to the run owner."
        else:
            if self.portfolio_id is not None:
                errors["portfolio"] = "Ad hoc optimization runs cannot reference a portfolio."
            if self.benchmark_asset_id is not None:
                errors["benchmark_asset"] = (
                    "Ad hoc optimization runs do not inherit a portfolio benchmark."
                )

        status = OptimizationRunStatus(self.status)
        if status in (OptimizationRunStatus.PENDING, OptimizationRunStatus.RUNNING):
            if self.result is not None:
                errors["result"] = "Pending/running optimization runs cannot have a result."
            if self.failure_code or self.failure_message:
                errors["failure_code"] = "Pending/running runs cannot have failure metadata."
        elif status == OptimizationRunStatus.SUCCEEDED:
            if self.result is None:
                errors["result"] = "Successful optimization runs require a result."
            if self.failure_code or self.failure_message:
                errors["failure_code"] = "Successful runs cannot have failure metadata."
            if self.completed_at is None:
                errors["completed_at"] = "Successful runs require completed_at."
        elif status == OptimizationRunStatus.FAILED:
            if self.result is not None:
                errors["result"] = "Failed optimization runs cannot have a successful result."
            if not self.failure_code.strip() or not self.failure_message.strip():
                errors["failure_code"] = "Failed runs require a code and message."
            if self.completed_at is None:
                errors["completed_at"] = "Failed runs require completed_at."

        try:
            _validate_json_finite(self.included_asset_ids)
            _validate_json_finite(self.baseline_weights)
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
            raise ValueError("Persisted optimization JSON cannot contain NaN or infinity.")
        return
    if isinstance(value, dict):
        for child in value.values():
            _validate_json_finite(child)
        return
    if isinstance(value, (list, tuple)):
        for child in value:
            _validate_json_finite(child)
