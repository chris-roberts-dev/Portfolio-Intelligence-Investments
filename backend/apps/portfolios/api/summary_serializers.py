"""DRF transport contracts for the P0 portfolio accounting summary."""

from rest_framework import serializers

from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)
from apps.portfolios.services.dashboard_summary import (
    DashboardPortfolioSummaryMetrics,
    DashboardPortfolioSummaryProvenance,
    DashboardPortfolioSummaryResult,
    PortfolioSummaryUnavailableReason,
)


class DashboardPortfolioSummaryMetricsSerializer(
    serializers.Serializer[DashboardPortfolioSummaryMetrics]
):
    """Exact Decimal dashboard accounting metrics."""

    total_market_value = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    total_market_value_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in PortfolioSummaryUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    net_contributions = serializers.CharField(read_only=True)
    cost_basis = serializers.CharField(read_only=True)
    cash_balance = serializers.CharField(read_only=True)
    cash_percentage = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    cash_percentage_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in PortfolioSummaryUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    unrealized_gain_loss = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    unrealized_gain_loss_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in PortfolioSummaryUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    selected_period_realized_gain_loss = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    selected_period_realized_gain_loss_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in PortfolioSummaryUnavailableReason],
        read_only=True,
        allow_null=True,
    )
    selected_period_income_received = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    selected_period_income_unavailable_reason = serializers.ChoiceField(
        choices=[reason.value for reason in PortfolioSummaryUnavailableReason],
        read_only=True,
        allow_null=True,
    )


class DashboardPortfolioSummaryProvenanceSerializer(
    serializers.Serializer[DashboardPortfolioSummaryProvenance]
):
    """Accounting and current-price provenance."""

    portfolio_id = serializers.UUIDField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    requested_start = serializers.DateField(read_only=True)
    requested_end_exclusive = serializers.DateField(read_only=True)
    ledger_as_of = serializers.DateTimeField(read_only=True)
    current_price_data_as_of = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    calculated_at = serializers.DateTimeField(read_only=True)
    current_price_field = serializers.CharField(read_only=True)
    accounting_method = serializers.CharField(read_only=True)
    accounting_assumptions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    selected_period_transaction_timezone = serializers.CharField(
        read_only=True,
    )
    net_contributions_scope = serializers.CharField(read_only=True)
    selected_period_accounting_scope = serializers.CharField(
        read_only=True,
    )


class DashboardPortfolioSummaryResultSerializer(
    serializers.Serializer[DashboardPortfolioSummaryResult]
):
    """Complete P0 portfolio-summary response."""

    metrics = DashboardPortfolioSummaryMetricsSerializer(read_only=True)
    data_quality = serializers.ChoiceField(
        choices=[state.value for state in PerformanceDataQualityState],
        read_only=True,
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    provenance = DashboardPortfolioSummaryProvenanceSerializer(
        read_only=True,
    )
