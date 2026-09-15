"""DRF transport contracts for the P0 allocation visualization."""

from typing import Any, cast

from rest_framework import serializers

from apps.portfolios.services.dashboard_allocation import (
    DashboardAllocationGroup,
    DashboardAllocationProvenance,
    DashboardAllocationResult,
    DashboardAllocationTotals,
    DashboardAllocationUnavailableReason,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)


class DashboardAllocationGroupSerializer(serializers.Serializer[DashboardAllocationGroup]):
    """One display-ready asset-class or cash allocation segment."""

    key = serializers.CharField(read_only=True)
    label = cast(
        Any,
        serializers.CharField(read_only=True),
    )
    is_cash = serializers.BooleanField(read_only=True)
    asset_count = serializers.IntegerField(read_only=True)
    market_value = serializers.CharField(read_only=True)
    weight = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )


class DashboardAllocationTotalsSerializer(serializers.Serializer[DashboardAllocationTotals]):
    """Current invested/cash totals for the allocation card."""

    total_market_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    invested_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    cash_value = serializers.CharField(read_only=True)
    invested_weight = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    cash_weight = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )


class DashboardAllocationProvenanceSerializer(
    serializers.Serializer[DashboardAllocationProvenance]
):
    """Current-pricing and grouping provenance."""

    portfolio_id = serializers.UUIDField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    as_of = serializers.DateTimeField(read_only=True)
    data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    calculated_at = serializers.DateTimeField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    grouping_dimension = serializers.CharField(read_only=True)
    supported_grouping_dimensions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    grouping_source = serializers.CharField(read_only=True)
    ordering_rule = serializers.CharField(read_only=True)
    other_grouping_applied = serializers.BooleanField(read_only=True)
    other_grouping_threshold = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    other_grouping_rule = serializers.CharField(read_only=True)
    weight_sum_tolerance = serializers.FloatField(read_only=True)


class DashboardAllocationResultSerializer(serializers.Serializer[DashboardAllocationResult]):
    """Complete P0 allocation-card backend contract."""

    allocation_available = serializers.BooleanField(read_only=True)
    groups = DashboardAllocationGroupSerializer(
        many=True,
        read_only=True,
    )
    totals = DashboardAllocationTotalsSerializer(read_only=True)
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in DashboardAllocationUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    provenance = DashboardAllocationProvenanceSerializer(
        read_only=True,
    )
