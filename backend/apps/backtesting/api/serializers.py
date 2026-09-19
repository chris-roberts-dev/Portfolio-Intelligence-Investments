"""Explicit DRF contracts for owner-scoped persisted backtest runs."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from rest_framework import serializers

from apps.backtesting.models import BacktestRun, BacktestRunStatus, BacktestStrategyName
from apps.backtesting.services import BacktestTargetWeightInput, CreateBacktestRunCommand
from portfolio_engine.config import (
    DEFAULT_COMMISSION_RATE,
    DEFAULT_SLIPPAGE_RATE,
    MAX_BAR_QUERY_SYMBOLS,
    WEIGHT_SUM_TOLERANCE,
)


class BacktestTargetWeightSerializer(serializers.Serializer[object]):
    asset_id = serializers.UUIDField()
    weight = serializers.FloatField(min_value=0.0, max_value=1.0)

    def validate_weight(self, value: float) -> float:
        if not math.isfinite(value):
            raise serializers.ValidationError("Target weight must be finite.")
        return value


class BacktestRunCreateRequestSerializer(serializers.Serializer[object]):
    strategy = serializers.ChoiceField(
        choices=BacktestStrategyName.choices,
        default=BacktestStrategyName.BUY_AND_HOLD,
    )
    start = serializers.DateField()
    end = serializers.DateField()
    initial_cash = serializers.DecimalField(
        max_digits=24,
        decimal_places=8,
        min_value=Decimal("0.00000001"),
    )
    target_weights = BacktestTargetWeightSerializer(
        many=True,
        allow_empty=False,
    )
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

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["end"] <= attrs["start"]:
            raise serializers.ValidationError({"end": "end must be later than start."})

        strategy = BacktestStrategyName(cast(str, attrs["strategy"]))
        if strategy is not BacktestStrategyName.BUY_AND_HOLD:
            raise serializers.ValidationError(
                {"strategy": "Only BUY_AND_HOLD is implemented in this Phase 6 batch."}
            )

        raw_weights = cast(list[dict[str, Any]], attrs["target_weights"])
        if len(raw_weights) > MAX_BAR_QUERY_SYMBOLS:
            raise serializers.ValidationError(
                {
                    "target_weights": (
                        f"No more than {MAX_BAR_QUERY_SYMBOLS} target weights may be supplied."
                    )
                }
            )

        asset_ids = tuple(cast(UUID, item["asset_id"]) for item in raw_weights)
        if len(set(asset_ids)) != len(asset_ids):
            raise serializers.ValidationError(
                {"target_weights": "Each asset may appear at most once."}
            )
        total = math.fsum(float(item["weight"]) for item in raw_weights)
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise serializers.ValidationError(
                {"target_weights": "Target weights must sum to one within tolerance."}
            )

        for field_name in ("commission_rate", "slippage_rate"):
            value = float(attrs[field_name])
            if not math.isfinite(value):
                raise serializers.ValidationError({field_name: f"{field_name} must be finite."})
        return attrs

    def to_command(self) -> CreateBacktestRunCommand:
        data = cast(dict[str, Any], self.validated_data)
        raw_weights = cast(list[dict[str, Any]], data["target_weights"])
        return CreateBacktestRunCommand(
            strategy=BacktestStrategyName(cast(str, data["strategy"])),
            period_start=data["start"],
            period_end_exclusive=data["end"],
            initial_cash=float(cast(Decimal, data["initial_cash"])),
            target_weights=tuple(
                BacktestTargetWeightInput(
                    asset_id=cast(UUID, item["asset_id"]),
                    weight=float(item["weight"]),
                )
                for item in raw_weights
            ),
            commission_rate=float(data["commission_rate"]),
            slippage_rate=float(data["slippage_rate"]),
        )


class BacktestWarningSerializer(serializers.Serializer[object]):
    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class BacktestOrderSerializer(serializers.Serializer[object]):
    asset_id = serializers.UUIDField(read_only=True)
    side = serializers.CharField(read_only=True)
    quantity = serializers.FloatField(read_only=True)


class BacktestFillSerializer(serializers.Serializer[object]):
    asset_id = serializers.UUIDField(read_only=True)
    side = serializers.CharField(read_only=True)
    quantity = serializers.FloatField(read_only=True)
    reference_price = serializers.FloatField(read_only=True)
    fill_price = serializers.FloatField(read_only=True)
    fill_notional = serializers.FloatField(read_only=True)
    commission_cost = serializers.FloatField(read_only=True)
    slippage_cost = serializers.FloatField(read_only=True)


class BacktestPositionSnapshotSerializer(serializers.Serializer[object]):
    asset_id = serializers.UUIDField(read_only=True)
    quantity = serializers.FloatField(read_only=True)
    market_value = serializers.FloatField(read_only=True)
    weight = serializers.FloatField(read_only=True)


class BacktestPortfolioStateSerializer(serializers.Serializer[object]):
    as_of = serializers.DateField(read_only=True)
    positions = BacktestPositionSnapshotSerializer(many=True, read_only=True)
    cash = serializers.FloatField(read_only=True)
    cash_weight = serializers.FloatField(read_only=True)
    total_value = serializers.FloatField(read_only=True)


class BacktestEquityObservationSerializer(serializers.Serializer[object]):
    trade_date = serializers.DateField(read_only=True)
    portfolio_value = serializers.FloatField(read_only=True)


class BacktestReturnObservationSerializer(serializers.Serializer[object]):
    trade_date = serializers.DateField(read_only=True)
    simple_return = serializers.FloatField(read_only=True)


class BacktestDecisionSerializer(serializers.Serializer[object]):
    decision_date = serializers.DateField(read_only=True)
    orders = BacktestOrderSerializer(many=True, read_only=True)


class BacktestExecutionSerializer(serializers.Serializer[object]):
    decision_date = serializers.DateField(read_only=True)
    execution_date = serializers.DateField(read_only=True)
    orders = BacktestOrderSerializer(many=True, read_only=True)
    fills = BacktestFillSerializer(many=True, read_only=True)
    pre_trade_value = serializers.FloatField(read_only=True)
    post_trade_value = serializers.FloatField(read_only=True)
    turnover = serializers.FloatField(read_only=True)
    commission_cost = serializers.FloatField(read_only=True)
    slippage_cost = serializers.FloatField(read_only=True)
    total_cost = serializers.FloatField(read_only=True)
    buy_scale = serializers.FloatField(read_only=True)


class BacktestCostObservationSerializer(serializers.Serializer[object]):
    execution_date = serializers.DateField(read_only=True)
    commission_cost = serializers.FloatField(read_only=True)
    slippage_cost = serializers.FloatField(read_only=True)
    total_cost = serializers.FloatField(read_only=True)


class BacktestSummarySerializer(serializers.Serializer[object]):
    initial_value = serializers.FloatField(read_only=True)
    ending_value = serializers.FloatField(read_only=True)
    cumulative_return = serializers.FloatField(read_only=True)
    trade_count = serializers.IntegerField(read_only=True)
    turnover = serializers.FloatField(read_only=True)
    commission_cost = serializers.FloatField(read_only=True)
    slippage_cost = serializers.FloatField(read_only=True)
    total_cost = serializers.FloatField(read_only=True)


class BacktestAssumptionsSerializer(serializers.Serializer[object]):
    price_field = serializers.CharField(read_only=True)
    execution_timing = serializers.CharField(read_only=True)
    commission_rate = serializers.FloatField(read_only=True)
    slippage_rate = serializers.FloatField(read_only=True)
    turnover_convention = serializers.CharField(read_only=True)
    fractional_shares = serializers.BooleanField(read_only=True)
    long_only = serializers.BooleanField(read_only=True)
    leverage = serializers.BooleanField(read_only=True)


class BacktestResultProvenanceSerializer(serializers.Serializer[object]):
    provider = serializers.CharField(read_only=True)
    retrieved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    data_fingerprint = serializers.CharField(read_only=True, allow_null=True)
    requested_period_start = serializers.DateField(read_only=True)
    requested_period_end_exclusive = serializers.DateField(read_only=True)
    aligned_period_start = serializers.DateField(read_only=True)
    aligned_period_end = serializers.DateField(read_only=True)
    engine_version = serializers.CharField(read_only=True)
    backtest_method_version = serializers.CharField(read_only=True)
    strategy_name = serializers.CharField(read_only=True)
    strategy_version = serializers.CharField(read_only=True)


class BacktestResultSerializer(serializers.Serializer[object]):
    aligned_dates = serializers.ListField(child=serializers.DateField(), read_only=True)
    snapshots = BacktestPortfolioStateSerializer(many=True, read_only=True)
    equity_curve = BacktestEquityObservationSerializer(many=True, read_only=True)
    returns = BacktestReturnObservationSerializer(many=True, read_only=True)
    decisions = BacktestDecisionSerializer(many=True, read_only=True)
    executions = BacktestExecutionSerializer(many=True, read_only=True)
    costs = BacktestCostObservationSerializer(many=True, read_only=True)
    summary = BacktestSummarySerializer(read_only=True)
    assumptions = BacktestAssumptionsSerializer(read_only=True)
    provenance = BacktestResultProvenanceSerializer(read_only=True)
    warnings = BacktestWarningSerializer(many=True, read_only=True)


class BacktestRunProvenanceSerializer(serializers.Serializer[BacktestRun]):
    requested_period_start = serializers.DateField(source="period_start", read_only=True)
    requested_period_end_exclusive = serializers.DateField(
        source="period_end_exclusive",
        read_only=True,
    )
    provider = serializers.CharField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    engine_version = serializers.CharField(read_only=True)
    backtest_method_version = serializers.CharField(source="method_version", read_only=True)
    strategy_version = serializers.CharField(read_only=True)
    data_retrieved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    data_fingerprint = serializers.CharField(read_only=True, allow_blank=True)


class BacktestRunSerializer(serializers.Serializer[BacktestRun]):
    id = serializers.UUIDField(read_only=True)
    status = serializers.ChoiceField(choices=BacktestRunStatus.choices, read_only=True)
    strategy = serializers.ChoiceField(choices=BacktestStrategyName.choices, read_only=True)
    included_asset_ids = serializers.ListField(child=serializers.UUIDField(), read_only=True)
    parameters = serializers.JSONField(read_only=True)
    initial_cash = serializers.DecimalField(max_digits=24, decimal_places=8, read_only=True)
    commission_rate = serializers.DecimalField(max_digits=18, decimal_places=12, read_only=True)
    slippage_rate = serializers.DecimalField(max_digits=18, decimal_places=12, read_only=True)
    result = BacktestResultSerializer(allow_null=True, read_only=True)
    warnings = BacktestWarningSerializer(many=True, read_only=True)
    failure_code = serializers.CharField(read_only=True, allow_blank=True)
    failure_message = serializers.CharField(read_only=True, allow_blank=True)
    started_at = serializers.DateTimeField(read_only=True, allow_null=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    provenance = BacktestRunProvenanceSerializer(source="*", read_only=True)


class BacktestApiErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField()
    detail = serializers.CharField()


class BacktestValidationErrorSerializer(serializers.Serializer[object]):
    code = serializers.CharField()
    errors = serializers.DictField()  # type: ignore[assignment]  # DRF metaclass field
