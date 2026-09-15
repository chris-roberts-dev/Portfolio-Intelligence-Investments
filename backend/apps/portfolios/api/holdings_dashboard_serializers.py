"""DRF transport contracts for dashboard holdings and selected-period movement."""

from rest_framework import serializers

from apps.portfolios.services.dashboard_holdings import (
    DashboardHolding,
    DashboardHoldingsProvenance,
    DashboardHoldingsResult,
    DashboardHoldingWarning,
    HoldingMetricUnavailableReason,
    HoldingSparklinePoint,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)


class HoldingSparklinePointSerializer(serializers.Serializer[HoldingSparklinePoint]):
    """One exact-date adjusted-close point; missing data stays null."""

    observation_date = serializers.DateField(read_only=True)
    adjusted_close = serializers.CharField(
        read_only=True,
        allow_null=True,
    )


class DashboardHoldingWarningSerializer(serializers.Serializer[DashboardHoldingWarning]):
    """One structured holding-level data-quality warning."""

    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    asset_id = serializers.UUIDField(read_only=True)
    symbol = serializers.CharField(read_only=True)
    observation_date = serializers.DateField(
        read_only=True,
        allow_null=True,
    )


class DashboardHoldingSerializer(serializers.Serializer[DashboardHolding]):
    """One dashboard-ready current holding."""

    asset_id = serializers.UUIDField(read_only=True)
    symbol = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    asset_type = serializers.CharField(read_only=True)
    currency = serializers.CharField(read_only=True)
    quantity = serializers.CharField(read_only=True)
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
    weight_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in HoldingMetricUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    selected_period_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    selected_period_return_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in HoldingMetricUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    contribution_to_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    contribution_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in HoldingMetricUnavailableReason],
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
    warnings = DashboardHoldingWarningSerializer(
        many=True,
        read_only=True,
    )


class DashboardHoldingsProvenanceSerializer(serializers.Serializer[DashboardHoldingsProvenance]):
    """Current and selected-period holdings provenance."""

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


class DashboardHoldingsResultSerializer(serializers.Serializer[DashboardHoldingsResult]):
    """Complete P0 dashboard holdings response contract."""

    holdings = DashboardHoldingSerializer(
        many=True,
        read_only=True,
    )
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    warnings = DashboardHoldingWarningSerializer(
        many=True,
        read_only=True,
    )
    provenance = DashboardHoldingsProvenanceSerializer(
        read_only=True,
    )
