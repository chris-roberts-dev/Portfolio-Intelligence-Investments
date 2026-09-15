"""DRF transport contracts for dashboard portfolio performance series."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from rest_framework import serializers

from apps.portfolios.api.contracts import PortfolioProviderQuerySerializer
from apps.portfolios.services.dashboard_performance import (
    BenchmarkPerformancePoint,
    DashboardPerformanceProvenance,
    DashboardPerformanceResult,
    DashboardPerformanceWarning,
    PerformanceDataQualityState,
    PortfolioPerformancePoint,
    PortfolioPerformanceSummary,
)


class PortfolioPerformanceQuerySerializer(PortfolioProviderQuerySerializer):
    """Inclusive-start/exclusive-end dashboard performance query."""

    start = serializers.DateField()
    end = serializers.DateField()

    @property
    def start_date(self) -> date:
        return cast(date, self.validated_data["start"])

    @property
    def end_date(self) -> date:
        return cast(date, self.validated_data["end"])

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        start = cast(date, attrs["start"])
        end = cast(date, attrs["end"])

        if end <= start:
            raise serializers.ValidationError(
                {"end": ["end must be after start; end is exclusive."]}
            )

        return attrs


class PortfolioPerformanceSummarySerializer(serializers.Serializer[PortfolioPerformanceSummary]):
    """Headline selected-period values."""

    starting_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    ending_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    value_change = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    net_external_flow = serializers.CharField(read_only=True)
    investment_gain_loss = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    cumulative_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    benchmark_cumulative_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )


class PortfolioPerformancePointSerializer(serializers.Serializer[PortfolioPerformancePoint]):
    """One chart-ready portfolio point."""

    observation_date = serializers.DateField(read_only=True)
    portfolio_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    net_external_flow = serializers.CharField(read_only=True)
    daily_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    cumulative_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class BenchmarkPerformancePointSerializer(serializers.Serializer[BenchmarkPerformancePoint]):
    """One exact-date benchmark point; gaps remain explicit nulls."""

    observation_date = serializers.DateField(read_only=True)
    adjusted_close = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    cumulative_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )


class DashboardPerformanceWarningSerializer(serializers.Serializer[DashboardPerformanceWarning]):
    """One display-ready portfolio or benchmark warning."""

    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    observation_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )
    asset_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    symbol = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class DashboardPerformanceProvenanceSerializer(
    serializers.Serializer[DashboardPerformanceProvenance]
):
    """Requested/effective ranges plus data/calculation provenance."""

    portfolio_id = serializers.UUIDField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    requested_start = serializers.DateField(read_only=True)
    requested_end_exclusive = serializers.DateField(read_only=True)
    effective_start = serializers.DateField(read_only=True)
    effective_end_exclusive = serializers.DateField(read_only=True)
    data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    calculated_at = serializers.DateTimeField(read_only=True)
    engine_version = serializers.CharField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    benchmark_asset_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    benchmark_symbol = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class DashboardPerformanceResultSerializer(serializers.Serializer[DashboardPerformanceResult]):
    """Complete performance-hero backend response contract."""

    summary = PortfolioPerformanceSummarySerializer(read_only=True)
    points = PortfolioPerformancePointSerializer(
        many=True,
        read_only=True,
    )
    benchmark_points = BenchmarkPerformancePointSerializer(
        many=True,
        read_only=True,
    )
    portfolio_data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    benchmark_data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
        allow_null=True,
    )
    warnings = DashboardPerformanceWarningSerializer(
        many=True,
        read_only=True,
    )
    provenance = DashboardPerformanceProvenanceSerializer(
        read_only=True,
    )
