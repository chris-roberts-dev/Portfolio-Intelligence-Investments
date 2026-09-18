"""Persisted target allocations and Phase 5 rebalance simulation/comparison resources."""

from __future__ import annotations

import math
import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TargetAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="target_allocations",
    )
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        on_delete=models.CASCADE,
        related_name="target_allocations",
    )
    source_optimization_run = models.ForeignKey(
        "optimization.OptimizationRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="target_allocations",
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=~Q(name=""),
                name="target_allocation_name_nonblank",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.portfolio_id})"

    def clean(self) -> None:
        super().clean()

        errors: dict[str, str] = {}

        if self.user_id and self.portfolio_id and self.portfolio.user_id != self.user_id:
            errors["portfolio"] = "portfolio must belong to the target owner."

        if self.source_optimization_run_id is not None:
            run = self.source_optimization_run
            if run is None:
                errors["source_optimization_run"] = "source run could not be resolved."
            elif run.user_id != self.user_id or run.portfolio_id != self.portfolio_id:
                errors["source_optimization_run"] = (
                    "source run must belong to the same user and portfolio."
                )

        if errors:
            raise ValidationError(errors)


class TargetAllocationWeight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(
        TargetAllocation,
        on_delete=models.CASCADE,
        related_name="weights",
    )
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="target_allocation_weights",
    )
    is_cash = models.BooleanField(default=False)
    weight = models.DecimalField(
        max_digits=18,
        decimal_places=12,
    )

    class Meta:
        ordering = ("is_cash", "asset_id", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(weight__gte=0) & Q(weight__lte=1),
                name="target_weight_unit_interval",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_cash=True, asset__isnull=True) | Q(is_cash=False, asset__isnull=False)
                ),
                name="target_weight_cash_identity_consistent",
            ),
            models.UniqueConstraint(
                fields=("target", "asset"),
                name="target_allocation_asset_uniq",
            ),
            models.UniqueConstraint(
                fields=("target",),
                condition=Q(is_cash=True),
                name="target_allocation_single_cash",
            ),
        ]

    def __str__(self) -> str:
        identity = "CASH" if self.is_cash else str(self.asset_id)
        return f"{self.target_id}:{identity}={self.weight}"


class RebalanceSimulation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rebalance_simulations",
    )
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        on_delete=models.CASCADE,
        related_name="rebalance_simulations",
    )
    target_allocation = models.ForeignKey(
        TargetAllocation,
        on_delete=models.PROTECT,
        related_name="rebalance_simulations",
    )
    as_of = models.DateTimeField()
    provider = models.CharField(max_length=32)
    price_field = models.CharField(max_length=32, default="close")
    valuation_retrieved_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    drift_threshold = models.DecimalField(
        max_digits=18,
        decimal_places=12,
        null=True,
        blank=True,
    )
    schedule = models.CharField(
        max_length=16,
        blank=True,
    )
    previous_rebalance_date = models.DateField(
        null=True,
        blank=True,
    )
    result = models.JSONField()
    warnings = models.JSONField(
        default=list,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return f"RebalanceSimulation {self.id} ({self.portfolio_id})"

    def clean(self) -> None:
        super().clean()

        errors: dict[str, str] = {}

        if self.user_id and self.portfolio_id and self.portfolio.user_id != self.user_id:
            errors["portfolio"] = "portfolio must belong to the simulation owner."

        if self.target_allocation_id and self.portfolio_id:
            target = self.target_allocation
            if target.user_id != self.user_id or target.portfolio_id != self.portfolio_id:
                errors["target_allocation"] = (
                    "target allocation must belong to the same user and portfolio."
                )

        if self.price_field != "close":
            errors["price_field"] = "Current rebalance simulations must use raw close valuation."

        if self.drift_threshold is not None and not (
            Decimal("0") <= self.drift_threshold <= Decimal("1")
        ):
            errors["drift_threshold"] = "drift_threshold must be between zero and one."

        try:
            _validate_json_finite(self.result)
            _validate_json_finite(self.warnings)
        except ValueError as exc:
            errors["result"] = str(exc)

        if errors:
            raise ValidationError(errors)


class HistoricalRebalanceComparison(models.Model):
    """Persisted deterministic comparison of historical rebalancing policies."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="historical_rebalance_comparisons",
    )
    portfolio = models.ForeignKey(
        "portfolios.Portfolio",
        on_delete=models.CASCADE,
        related_name="historical_rebalance_comparisons",
    )
    target_allocation = models.ForeignKey(
        TargetAllocation,
        on_delete=models.PROTECT,
        related_name="historical_rebalance_comparisons",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    provider = models.CharField(max_length=32)
    price_field = models.CharField(max_length=32, default="adjusted_close")
    retrieved_at = models.DateTimeField(null=True, blank=True)
    drift_threshold = models.DecimalField(max_digits=18, decimal_places=12)
    commission_rate = models.DecimalField(max_digits=18, decimal_places=12, default=Decimal("0"))
    slippage_rate = models.DecimalField(max_digits=18, decimal_places=12, default=Decimal("0"))
    engine_version = models.CharField(max_length=64)
    result = models.JSONField()
    warnings = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return f"HistoricalRebalanceComparison {self.id} ({self.portfolio_id})"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if self.user_id and self.portfolio_id and self.portfolio.user_id != self.user_id:
            errors["portfolio"] = "portfolio must belong to the comparison owner."

        if self.target_allocation_id and self.portfolio_id:
            target = self.target_allocation
            if target.user_id != self.user_id or target.portfolio_id != self.portfolio_id:
                errors["target_allocation"] = (
                    "target allocation must belong to the same user and portfolio."
                )

        if self.period_start >= self.period_end:
            errors["period_end"] = "period_end must be later than period_start."

        if self.price_field != "adjusted_close":
            errors["price_field"] = (
                "Historical rebalancing comparisons must use adjusted_close history."
            )

        for field_name in ("drift_threshold", "commission_rate", "slippage_rate"):
            value = getattr(self, field_name)
            if not (Decimal("0") <= value <= Decimal("1")):
                errors[field_name] = f"{field_name} must be between zero and one."

        try:
            _validate_json_finite(self.result)
            _validate_json_finite(self.warnings)
        except ValueError as exc:
            errors["result"] = str(exc)

        if errors:
            raise ValidationError(errors)


def _validate_json_finite(value: Any) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Persisted rebalance JSON cannot contain NaN or infinity.")
        return

    if isinstance(value, dict):
        for child in value.values():
            _validate_json_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_json_finite(child)
