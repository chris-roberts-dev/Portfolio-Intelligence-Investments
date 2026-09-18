"""Explicit DRF serializers for Phase 5 rebalancing resources."""

from __future__ import annotations

import math
from typing import Any, cast
from uuid import UUID

from rest_framework import serializers

from apps.rebalancing.models import (
    HistoricalRebalanceComparison,
    RebalanceSimulation,
    TargetAllocation,
    TargetAllocationWeight,
)
from apps.rebalancing.services import (
    CreateHistoricalRebalanceComparisonCommand,
    CreateRebalanceSimulationCommand,
    CreateTargetAllocationCommand,
    TargetWeightInput,
)
from portfolio_engine.config import DEFAULT_COMMISSION_RATE, DEFAULT_SLIPPAGE_RATE
from portfolio_engine.rebalancing import RebalanceSchedule

MAX_TARGET_WEIGHTS = 100


class TargetWeightRequestSerializer(serializers.Serializer[object]):
    asset_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    weight = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
    )


class TargetAllocationCreateRequestSerializer(serializers.Serializer[object]):
    portfolio_id = serializers.UUIDField()
    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
    weights = TargetWeightRequestSerializer(
        many=True,
        allow_empty=False,
    )
    source_optimization_run_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    def validate(
        self,
        attrs: dict[str, Any],
    ) -> dict[str, Any]:
        raw_weights = cast(
            list[dict[str, Any]],
            attrs["weights"],
        )

        if len(raw_weights) > MAX_TARGET_WEIGHTS:
            raise serializers.ValidationError(
                {"weights": (f"At most {MAX_TARGET_WEIGHTS} target weights are allowed.")}
            )

        ids = tuple(
            cast(
                UUID | None,
                item.get("asset_id"),
            )
            for item in raw_weights
        )

        if len(set(ids)) != len(ids):
            raise serializers.ValidationError(
                {"weights": ("Each asset/cash target may appear at most once.")}
            )

        total = 0.0

        for item in raw_weights:
            weight = float(item["weight"])

            if not math.isfinite(weight):
                raise serializers.ValidationError({"weights": "Target weights must be finite."})

            total += weight

        if abs(total - 1.0) > 1e-8:
            raise serializers.ValidationError({"weights": "Target weights must sum to one."})

        return attrs

    def to_command(self) -> CreateTargetAllocationCommand:
        data = cast(
            dict[str, Any],
            self.validated_data,
        )
        raw_weights = cast(
            list[dict[str, Any]],
            data["weights"],
        )

        return CreateTargetAllocationCommand(
            portfolio_id=cast(
                UUID,
                data["portfolio_id"],
            ),
            name=cast(
                str,
                data["name"],
            ),
            weights=tuple(
                TargetWeightInput(
                    asset_id=cast(
                        UUID | None,
                        item.get("asset_id"),
                    ),
                    weight=float(
                        item["weight"],
                    ),
                )
                for item in raw_weights
            ),
            source_optimization_run_id=cast(
                UUID | None,
                data.get("source_optimization_run_id"),
            ),
        )


class TargetAllocationWeightSerializer(serializers.Serializer[TargetAllocationWeight]):
    asset_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    is_cash = serializers.BooleanField(
        read_only=True,
    )
    weight = serializers.FloatField(
        read_only=True,
    )


class TargetAllocationSerializer(serializers.Serializer[TargetAllocation]):
    id = serializers.UUIDField(read_only=True)
    portfolio_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    source_optimization_run_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    weights = TargetAllocationWeightSerializer(
        many=True,
        read_only=True,
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class RebalanceSimulationCreateRequestSerializer(serializers.Serializer[object]):
    portfolio_id = serializers.UUIDField()
    target_allocation_id = serializers.UUIDField()
    drift_threshold = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
    )
    schedule = serializers.ChoiceField(
        required=False,
        choices=[item.value for item in RebalanceSchedule],
    )
    previous_rebalance_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    def to_command(self) -> CreateRebalanceSimulationCommand:
        data = cast(
            dict[str, Any],
            self.validated_data,
        )
        schedule_raw = cast(
            str | None,
            data.get("schedule"),
        )
        threshold_raw = data.get("drift_threshold")

        return CreateRebalanceSimulationCommand(
            portfolio_id=cast(
                UUID,
                data["portfolio_id"],
            ),
            target_allocation_id=cast(
                UUID,
                data["target_allocation_id"],
            ),
            drift_threshold=(float(threshold_raw) if threshold_raw is not None else None),
            schedule=(RebalanceSchedule(schedule_raw) if schedule_raw is not None else None),
            previous_rebalance_date=data.get("previous_rebalance_date"),
        )


class RebalanceSimulationSerializer(serializers.Serializer[RebalanceSimulation]):
    id = serializers.UUIDField(read_only=True)
    portfolio_id = serializers.UUIDField(read_only=True)
    target_allocation_id = serializers.UUIDField(read_only=True)
    as_of = serializers.DateTimeField(read_only=True)
    provider = serializers.CharField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    valuation_retrieved_at = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    drift_threshold = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    schedule = serializers.CharField(
        read_only=True,
        allow_blank=True,
    )
    previous_rebalance_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )
    result = serializers.JSONField(read_only=True)
    warnings = serializers.JSONField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class HistoricalRebalanceComparisonCreateRequestSerializer(serializers.Serializer[object]):
    portfolio_id = serializers.UUIDField()
    target_allocation_id = serializers.UUIDField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    drift_threshold = serializers.FloatField(min_value=0.0, max_value=1.0)
    commission_rate = serializers.FloatField(
        required=False,
        default=DEFAULT_COMMISSION_RATE,
        min_value=0.0,
        max_value=1.0,
    )
    slippage_rate = serializers.FloatField(
        required=False,
        default=DEFAULT_SLIPPAGE_RATE,
        min_value=0.0,
        max_value=1.0,
    )
    include_monthly = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["period_start"] >= attrs["period_end"]:
            raise serializers.ValidationError(
                {"period_end": "period_end must be later than period_start."}
            )
        return attrs

    def to_command(self) -> CreateHistoricalRebalanceComparisonCommand:
        data = cast(dict[str, Any], self.validated_data)
        return CreateHistoricalRebalanceComparisonCommand(
            portfolio_id=cast(UUID, data["portfolio_id"]),
            target_allocation_id=cast(UUID, data["target_allocation_id"]),
            period_start=data["period_start"],
            period_end=data["period_end"],
            drift_threshold=float(data["drift_threshold"]),
            commission_rate=float(data["commission_rate"]),
            slippage_rate=float(data["slippage_rate"]),
            include_monthly=bool(data["include_monthly"]),
        )


class HistoricalRebalanceComparisonSerializer(
    serializers.Serializer[HistoricalRebalanceComparison]
):
    id = serializers.UUIDField(read_only=True)
    portfolio_id = serializers.UUIDField(read_only=True)
    target_allocation_id = serializers.UUIDField(read_only=True)
    period_start = serializers.DateField(read_only=True)
    period_end = serializers.DateField(read_only=True)
    provider = serializers.CharField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    retrieved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    drift_threshold = serializers.FloatField(read_only=True)
    commission_rate = serializers.FloatField(read_only=True)
    slippage_rate = serializers.FloatField(read_only=True)
    engine_version = serializers.CharField(read_only=True)
    result = serializers.JSONField(read_only=True)
    warnings = serializers.JSONField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class RebalancingApiErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


class RebalancingValidationErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField(read_only=True)
    errors = serializers.DictField(  # type: ignore[assignment]
        read_only=True,
    )
