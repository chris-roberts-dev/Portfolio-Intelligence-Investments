"""DRF transport contracts for P1 dashboard mover rankings."""

from __future__ import annotations

from typing import cast

from rest_framework import serializers

from apps.portfolios.api.holdings_dashboard_serializers import (
    HoldingSparklinePointSerializer,
)
from apps.portfolios.api.performance_serializers import (
    PortfolioPerformanceQuerySerializer,
)
from apps.portfolios.services.dashboard_movers import (
    DashboardMover,
    DashboardMoversProvenance,
    DashboardMoversResult,
    MoversReconciliation,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)


class PortfolioMoversQuerySerializer(PortfolioPerformanceQuerySerializer):
    """Selected-period mover query with a bounded per-ranking result limit."""

    limit = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20,
    )

    @property
    def result_limit(self) -> int:
        return cast(int, self.validated_data["limit"])


class DashboardMoverSerializer(serializers.Serializer[DashboardMover]):
    """One ranked security with current-holding and period metrics."""

    asset_id = serializers.UUIDField(read_only=True)
    symbol = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    asset_type = serializers.CharField(read_only=True)
    currency = serializers.CharField(read_only=True)
    is_current_holding = serializers.BooleanField(read_only=True)
    quantity = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    current_price = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    current_price_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )
    current_price_retrieved_at = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    stale_trading_sessions = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    market_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    weight = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    selected_period_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    contribution_to_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    sparkline = HoldingSparklinePointSerializer(
        many=True,
        read_only=True,
    )
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    unavailable_reasons = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class MoversReconciliationSerializer(serializers.Serializer[MoversReconciliation]):
    """Portfolio-TWR reconciliation metadata for contribution rankings."""

    status = serializers.CharField(read_only=True)
    periods = serializers.IntegerField(read_only=True)
    cumulative_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    asset_contribution_total = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    unattributed_contribution = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    reconciliation_error = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    unavailable_reason = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class DashboardMoversProvenanceSerializer(serializers.Serializer[DashboardMoversProvenance]):
    """Provider, period, calculation, and attribution provenance."""

    portfolio_id = serializers.UUIDField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    requested_start = serializers.DateField(read_only=True)
    requested_end_exclusive = serializers.DateField(read_only=True)
    effective_start = serializers.DateField(read_only=True)
    effective_end_exclusive = serializers.DateField(read_only=True)
    current_price_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    period_data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    calculated_at = serializers.DateTimeField(read_only=True)
    current_price_field = serializers.CharField(read_only=True)
    period_price_field = serializers.CharField(read_only=True)
    attribution_method = serializers.CharField(read_only=True)
    engine_version = serializers.CharField(read_only=True)


class DashboardMoversResultSerializer(serializers.Serializer[DashboardMoversResult]):
    """Complete P1 dashboard mover-ranking response."""

    top_gainers = DashboardMoverSerializer(
        many=True,
        read_only=True,
    )
    top_losers = DashboardMoverSerializer(
        many=True,
        read_only=True,
    )
    largest_contributors = DashboardMoverSerializer(
        many=True,
        read_only=True,
    )
    largest_detractors = DashboardMoverSerializer(
        many=True,
        read_only=True,
    )
    reconciliation = MoversReconciliationSerializer(read_only=True)
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    provenance = DashboardMoversProvenanceSerializer(read_only=True)
