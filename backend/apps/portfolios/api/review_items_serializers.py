"""DRF contracts for dashboard data-quality alerts and review items."""

from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from apps.portfolios.api.performance_serializers import (
    PortfolioPerformanceQuerySerializer,
)
from apps.portfolios.services.dashboard_review_items import (
    DashboardReviewCount,
    DashboardReviewCounts,
    DashboardReviewDrilldown,
    DashboardReviewFilters,
    DashboardReviewItem,
    DashboardReviewItemsResult,
    DashboardReviewProvenance,
    ReviewDrilldownResource,
    ReviewItemCategory,
    ReviewItemSeverity,
    ReviewItemSource,
)


class DashboardReviewItemsQuerySerializer(PortfolioPerformanceQuerySerializer):
    """Selected-period review-item query with optional detail filters."""

    severity = serializers.CharField(required=False)
    category = serializers.CharField(required=False)

    def validate_severity(self, value: str) -> str:
        normalized = value.strip().upper()

        try:
            return ReviewItemSeverity(normalized).value
        except ValueError as exc:
            raise serializers.ValidationError("severity must be ERROR, WARNING, or INFO.") from exc

    def validate_category(self, value: str) -> str:
        normalized = value.strip().upper()

        try:
            return ReviewItemCategory(normalized).value
        except ValueError as exc:
            allowed = ", ".join(category.value for category in ReviewItemCategory)
            raise serializers.ValidationError(f"category must be one of: {allowed}.") from exc

    @property
    def filter_severity(self) -> ReviewItemSeverity | None:
        value = cast(str | None, self.validated_data.get("severity"))
        return ReviewItemSeverity(value) if value is not None else None

    @property
    def filter_category(self) -> ReviewItemCategory | None:
        value = cast(str | None, self.validated_data.get("category"))
        return ReviewItemCategory(value) if value is not None else None


class DashboardReviewDrilldownSerializer(serializers.Serializer[DashboardReviewDrilldown]):
    """Owner-scoped semantic reference for investigating a review item."""

    resource = serializers.ChoiceField(
        choices=[resource.value for resource in ReviewDrilldownResource],
        read_only=True,
    )
    portfolio_id = serializers.UUIDField(read_only=True)
    requested_start = serializers.DateField(read_only=True)
    requested_end_exclusive = serializers.DateField(read_only=True)
    asset_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    symbol = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    observation_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )


class DashboardReviewItemSerializer(serializers.Serializer[DashboardReviewItem]):
    """One stable alert/review-item transport contract."""

    key = serializers.CharField(read_only=True)
    source = cast(
        Any,
        serializers.ChoiceField(
            choices=[source.value for source in ReviewItemSource],
            read_only=True,
        ),
    )
    severity = serializers.ChoiceField(
        choices=[severity.value for severity in ReviewItemSeverity],
        read_only=True,
    )
    category = serializers.ChoiceField(
        choices=[category.value for category in ReviewItemCategory],
        read_only=True,
    )
    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    drilldown = DashboardReviewDrilldownSerializer(read_only=True)


class DashboardReviewCountSerializer(serializers.Serializer[DashboardReviewCount]):
    """One severity/category count bucket."""

    key = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class DashboardReviewCountsSerializer(serializers.Serializer[DashboardReviewCounts]):
    """Unfiltered dashboard review counts."""

    total = serializers.IntegerField(read_only=True)
    by_severity = DashboardReviewCountSerializer(
        many=True,
        read_only=True,
    )
    by_category = DashboardReviewCountSerializer(
        many=True,
        read_only=True,
    )


class DashboardReviewFiltersSerializer(serializers.Serializer[DashboardReviewFilters]):
    """Filters applied to the detail-item collection."""

    severity = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    category = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class DashboardReviewProvenanceSerializer(serializers.Serializer[DashboardReviewProvenance]):
    """Calculation and source provenance for review-item aggregation."""

    portfolio_id = serializers.UUIDField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    requested_start = serializers.DateField(read_only=True)
    requested_end_exclusive = serializers.DateField(read_only=True)
    effective_start = serializers.DateField(read_only=True)
    effective_end_exclusive = serializers.DateField(read_only=True)
    current_data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    historical_data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    analytics_as_of_date = serializers.DateField(read_only=True)
    calculated_at = serializers.DateTimeField(read_only=True)
    engine_version = serializers.CharField(read_only=True)
    included_sources = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    ordering_rule = serializers.CharField(read_only=True)


class DashboardReviewItemsResultSerializer(serializers.Serializer[DashboardReviewItemsResult]):
    """Complete dashboard review-items response."""

    counts = DashboardReviewCountsSerializer(read_only=True)
    filtered_count = serializers.IntegerField(read_only=True)
    filters = DashboardReviewFiltersSerializer(read_only=True)
    items = DashboardReviewItemSerializer(
        many=True,
        read_only=True,
    )
    provenance = DashboardReviewProvenanceSerializer(read_only=True)
