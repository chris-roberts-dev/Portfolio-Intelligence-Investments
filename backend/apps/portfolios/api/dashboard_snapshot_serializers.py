"""DRF contracts for the canonical owner-scoped dashboard snapshot."""

from __future__ import annotations

from typing import cast

from rest_framework import serializers

from apps.portfolios.api.allocation_serializers import (
    DashboardAllocationResultSerializer,
)
from apps.portfolios.api.contracts import PortfolioAnalyticsQuerySerializer
from apps.portfolios.api.holdings_dashboard_serializers import (
    DashboardHoldingsResultSerializer,
)
from apps.portfolios.api.movers_serializers import DashboardMoversResultSerializer
from apps.portfolios.api.performance_serializers import (
    DashboardPerformanceResultSerializer,
)
from apps.portfolios.api.review_items_serializers import (
    DashboardReviewItemsResultSerializer,
)
from apps.portfolios.api.serializers import PortfolioAnalyticsResultSerializer
from apps.portfolios.api.summary_serializers import (
    DashboardPortfolioSummaryResultSerializer,
)
from apps.portfolios.services.dashboard_snapshot import (
    DashboardSnapshotContext,
    DashboardSnapshotModule,
    DashboardSnapshotModuleState,
    DashboardSnapshotModuleStatus,
    DashboardSnapshotResult,
)


class DashboardSnapshotQuerySerializer(PortfolioAnalyticsQuerySerializer):
    """Shared dashboard date/provider/assumption query contract."""

    movers_limit = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=20,
    )

    @property
    def movers_limit_value(self) -> int:
        return cast(int, self.validated_data["movers_limit"])


class DashboardSnapshotModuleStateSerializer(serializers.Serializer[DashboardSnapshotModuleState]):
    """One module's local snapshot availability state."""

    module = serializers.ChoiceField(
        choices=[module.value for module in DashboardSnapshotModule],
        read_only=True,
    )
    status = serializers.ChoiceField(
        choices=[status.value for status in DashboardSnapshotModuleStatus],
        read_only=True,
    )
    error_code = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    detail = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class DashboardSnapshotContextSerializer(serializers.Serializer[DashboardSnapshotContext]):
    """Immutable shared calculation and freshness context."""

    snapshot_id = serializers.UUIDField(read_only=True)
    portfolio_id = serializers.UUIDField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    requested_start = serializers.DateField(read_only=True)
    requested_end_exclusive = serializers.DateField(read_only=True)
    effective_start = serializers.DateField(read_only=True)
    effective_end_exclusive = serializers.DateField(read_only=True)
    valuation_cutoff = serializers.DateTimeField(read_only=True)
    calculated_at = serializers.DateTimeField(read_only=True)
    engine_version = serializers.CharField(read_only=True)
    current_data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    historical_data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    analytics_as_of_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )


class DashboardSnapshotResultSerializer(serializers.Serializer[DashboardSnapshotResult]):
    """Complete dashboard response with independently degradable modules."""

    snapshot = DashboardSnapshotContextSerializer(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    modules = DashboardSnapshotModuleStateSerializer(
        many=True,
        read_only=True,
    )
    summary = DashboardPortfolioSummaryResultSerializer(
        read_only=True,
        allow_null=True,
    )
    performance = DashboardPerformanceResultSerializer(
        read_only=True,
        allow_null=True,
    )
    allocation = DashboardAllocationResultSerializer(
        read_only=True,
        allow_null=True,
    )
    holdings = DashboardHoldingsResultSerializer(
        read_only=True,
        allow_null=True,
    )
    movers = DashboardMoversResultSerializer(
        read_only=True,
        allow_null=True,
    )
    analytics = PortfolioAnalyticsResultSerializer(
        read_only=True,
        allow_null=True,
    )
    review_items = DashboardReviewItemsResultSerializer(
        read_only=True,
        allow_null=True,
    )
