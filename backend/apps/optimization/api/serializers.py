"""Explicit DRF contracts for persisted optimization-run resources."""

from __future__ import annotations

import math
from typing import Any, cast
from uuid import UUID

from rest_framework import serializers

from apps.optimization.models import (
    OptimizationRun,
    OptimizationRunMethod,
    OptimizationRunSource,
    OptimizationRunStatus,
)
from apps.optimization.services import (
    AssetWeightBounds,
    BaselineWeight,
    CreateOptimizationRunCommand,
)


class OptimizationWeightBoundSerializer(serializers.Serializer[object]):
    """Optional per-asset long-only bound override."""

    asset_id = serializers.UUIDField()
    minimum = serializers.FloatField(min_value=0.0, max_value=1.0)
    maximum = serializers.FloatField(min_value=0.0, max_value=1.0)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        minimum = float(attrs["minimum"])
        maximum = float(attrs["maximum"])
        if not math.isfinite(minimum) or not math.isfinite(maximum):
            raise serializers.ValidationError({"minimum": "Weight bounds must be finite."})
        if minimum > maximum:
            raise serializers.ValidationError(
                {"maximum": "maximum must be greater than or equal to minimum."}
            )
        return attrs


class OptimizationBaselineWeightSerializer(serializers.Serializer[object]):
    """One optional reference-allocation weight for comparison only."""

    asset_id = serializers.UUIDField()
    weight = serializers.FloatField(min_value=0.0, max_value=1.0)

    def validate_weight(self, value: float) -> float:
        if not math.isfinite(value):
            raise serializers.ValidationError("Baseline weight must be finite.")
        return value


class OptimizationRunCreateRequestSerializer(serializers.Serializer[object]):
    """Request contract for one portfolio-derived or ad hoc persisted run."""

    source_type = serializers.ChoiceField(
        choices=OptimizationRunSource.choices,
        default=OptimizationRunSource.PORTFOLIO,
    )
    portfolio_id = serializers.UUIDField(required=False, allow_null=True)
    method = serializers.ChoiceField(choices=OptimizationRunMethod.choices)
    start = serializers.DateField()
    end = serializers.DateField()
    asset_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
        max_length=50,
    )
    bounds = OptimizationWeightBoundSerializer(
        many=True,
        required=False,
    )
    baseline_weights = OptimizationBaselineWeightSerializer(
        many=True,
        required=False,
    )
    risk_free_rate_annual = serializers.FloatField(required=False, default=0.0)
    frontier_points = serializers.IntegerField(
        required=False,
        default=25,
        min_value=2,
        max_value=100,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["end"] <= attrs["start"]:
            raise serializers.ValidationError({"end": "end must be later than start."})

        source_type = OptimizationRunSource(cast(str, attrs["source_type"]))
        portfolio_id = cast(UUID | None, attrs.get("portfolio_id"))
        raw_asset_ids = cast(list[UUID] | None, attrs.get("asset_ids"))

        if source_type is OptimizationRunSource.PORTFOLIO and portfolio_id is None:
            raise serializers.ValidationError(
                {"portfolio_id": "portfolio_id is required for PORTFOLIO runs."}
            )
        if source_type is OptimizationRunSource.AD_HOC:
            if portfolio_id is not None:
                raise serializers.ValidationError(
                    {"portfolio_id": "portfolio_id must be null/omitted for AD_HOC runs."}
                )
            if not raw_asset_ids:
                raise serializers.ValidationError(
                    {"asset_ids": "AD_HOC runs require an explicit non-empty asset_ids universe."}
                )

        risk_free_rate = float(attrs["risk_free_rate_annual"])
        if not math.isfinite(risk_free_rate):
            raise serializers.ValidationError(
                {"risk_free_rate_annual": "risk_free_rate_annual must be finite."}
            )

        asset_ids = tuple(raw_asset_ids or [])
        if len(set(asset_ids)) != len(asset_ids):
            raise serializers.ValidationError({"asset_ids": "asset_ids must be unique."})

        raw_bounds = cast(list[dict[str, Any]], attrs.get("bounds", []))
        bound_asset_ids = tuple(cast(UUID, bound["asset_id"]) for bound in raw_bounds)
        if len(set(bound_asset_ids)) != len(bound_asset_ids):
            raise serializers.ValidationError(
                {"bounds": "Each asset may appear in bounds at most once."}
            )
        if asset_ids and not set(bound_asset_ids).issubset(asset_ids):
            raise serializers.ValidationError(
                {"bounds": "Bound assets must be included in asset_ids when asset_ids is supplied."}
            )

        raw_baseline = cast(list[dict[str, Any]], attrs.get("baseline_weights", []))
        baseline_asset_ids = tuple(cast(UUID, item["asset_id"]) for item in raw_baseline)
        if len(set(baseline_asset_ids)) != len(baseline_asset_ids):
            raise serializers.ValidationError(
                {"baseline_weights": "Each asset may appear in baseline_weights at most once."}
            )
        if raw_baseline and asset_ids and set(baseline_asset_ids) != set(asset_ids):
            raise serializers.ValidationError(
                {
                    "baseline_weights": (
                        "A supplied baseline must include exactly every submitted asset."
                    )
                }
            )

        return attrs

    def to_command(self) -> CreateOptimizationRunCommand:
        """Map validated transport data into the typed application command."""
        data = cast(dict[str, Any], self.validated_data)
        raw_asset_ids = cast(list[UUID] | None, data.get("asset_ids"))
        raw_bounds = cast(list[dict[str, Any]], data.get("bounds", []))
        raw_baseline = cast(list[dict[str, Any]], data.get("baseline_weights", []))

        return CreateOptimizationRunCommand(
            source_type=OptimizationRunSource(cast(str, data["source_type"])),
            portfolio_id=cast(UUID | None, data.get("portfolio_id")),
            method=OptimizationRunMethod(cast(str, data["method"])),
            period_start=data["start"],
            period_end=data["end"],
            requested_asset_ids=(tuple(raw_asset_ids) if raw_asset_ids is not None else None),
            bounds=tuple(
                AssetWeightBounds(
                    asset_id=cast(UUID, bound["asset_id"]),
                    minimum=float(bound["minimum"]),
                    maximum=float(bound["maximum"]),
                )
                for bound in raw_bounds
            ),
            baseline_weights=tuple(
                BaselineWeight(
                    asset_id=cast(UUID, item["asset_id"]),
                    weight=float(item["weight"]),
                )
                for item in raw_baseline
            ),
            risk_free_rate_annual=float(data["risk_free_rate_annual"]),
            frontier_points=int(data["frontier_points"]),
        )


class OptimizationWeightSerializer(serializers.Serializer[object]):
    asset_id = serializers.UUIDField(read_only=True)
    weight = serializers.FloatField(read_only=True)


class OptimizedPortfolioSerializer(serializers.Serializer[object]):
    method = serializers.ChoiceField(choices=OptimizationRunMethod.choices, read_only=True)
    weights = OptimizationWeightSerializer(many=True, read_only=True)
    expected_return = serializers.FloatField(read_only=True)
    expected_volatility = serializers.FloatField(read_only=True)
    sharpe_ratio = serializers.FloatField(allow_null=True, read_only=True)
    target_return = serializers.FloatField(allow_null=True, read_only=True)


class OptimizationResultSerializer(serializers.Serializer[object]):
    portfolio = OptimizedPortfolioSerializer(allow_null=True, read_only=True)
    frontier = OptimizedPortfolioSerializer(many=True, read_only=True)


class OptimizationRunWarningSerializer(serializers.Serializer[object]):
    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class OptimizationRunProvenanceSerializer(serializers.Serializer[OptimizationRun]):
    period_start = serializers.DateField(read_only=True)
    period_end_exclusive = serializers.DateField(source="period_end", read_only=True)
    provider = serializers.CharField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    annualization_factor = serializers.IntegerField(read_only=True)
    risk_free_rate_annual = serializers.FloatField(read_only=True)
    benchmark_asset_id = serializers.UUIDField(allow_null=True, read_only=True)
    engine_version = serializers.CharField(read_only=True)
    method_version = serializers.CharField(read_only=True)
    data_retrieved_at = serializers.DateTimeField(allow_null=True, read_only=True)
    data_fingerprint = serializers.CharField(allow_blank=True, read_only=True)


class OptimizationRunSerializer(serializers.Serializer[OptimizationRun]):
    """Public persisted optimization-run response schema."""

    id = serializers.UUIDField(read_only=True)
    source_type = serializers.ChoiceField(
        choices=OptimizationRunSource.choices,
        read_only=True,
    )
    portfolio_id = serializers.UUIDField(read_only=True, allow_null=True)
    portfolio_name = serializers.CharField(
        source="portfolio.name",
        read_only=True,
        allow_null=True,
    )
    status = serializers.ChoiceField(choices=OptimizationRunStatus.choices, read_only=True)
    method = serializers.ChoiceField(choices=OptimizationRunMethod.choices, read_only=True)
    included_asset_ids = serializers.ListField(child=serializers.UUIDField(), read_only=True)
    baseline_weights = OptimizationBaselineWeightSerializer(many=True, read_only=True)
    parameters = serializers.JSONField(read_only=True)
    result = OptimizationResultSerializer(allow_null=True, read_only=True)
    warnings = OptimizationRunWarningSerializer(many=True, read_only=True)
    failure_code = serializers.CharField(allow_blank=True, read_only=True)
    failure_message = serializers.CharField(allow_blank=True, read_only=True)
    started_at = serializers.DateTimeField(allow_null=True, read_only=True)
    completed_at = serializers.DateTimeField(allow_null=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    provenance = OptimizationRunProvenanceSerializer(source="*", read_only=True)


class OptimizationApiErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField()
    detail = serializers.CharField()


class OptimizationValidationErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField()
    errors = serializers.DictField()  # type: ignore[assignment]  # DRF metaclass field
