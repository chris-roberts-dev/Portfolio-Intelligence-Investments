from __future__ import annotations

from datetime import datetime
from typing import cast

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.portfolios.models import Portfolio
from apps.portfolios.services.analytics import (
    PortfolioAnalyticsResult,
    PortfolioAnalyticsWarning,
    PortfolioAnalyticsWarningCode,
    RollingReturnObservation,
)
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentPositionPrice,
    CurrentValuationProvenance,
    CurrentValuationWarning,
    CurrentValuationWarningCode,
)
from portfolio_engine.contracts.analytical_result import (
    AnalyticalResultProvenance,
)
from portfolio_engine.performance.downside import SortinoRatioResult
from portfolio_engine.performance.drawdown import MaximumDrawdownResult
from portfolio_engine.performance.returns import AnnualizedReturnResult
from portfolio_engine.performance.statistics import SharpeRatioResult
from portfolio_engine.portfolio.allocation import (
    PortfolioAllocationResult,
    SecurityAllocation,
)
from portfolio_engine.portfolio.valuation import (
    PortfolioValuationResult,
    PositionValuationResult,
)
from portfolio_engine.risk.concentration import ConcentrationResult
from portfolio_engine.risk.relationships import (
    BetaResult,
    CorrelationResult,
)


class PortfolioSummarySerializer(serializers.Serializer[Portfolio]):
    """Read-only public portfolio summary."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    base_currency = serializers.CharField(read_only=True)
    benchmark_asset_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    ledger_inception_at = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_ledger_inception_at(self, obj: Portfolio) -> datetime | None:
        """Return the first authoritative ledger event, if one exists."""
        if hasattr(obj, "ledger_inception_at"):
            return cast(datetime | None, obj.ledger_inception_at)

        transactions = getattr(obj, "transactions", None)
        if transactions is None:
            return None

        return cast(
            datetime | None,
            transactions.order_by("occurred_at", "source_sequence", "id")
            .values_list("occurred_at", flat=True)
            .first(),
        )


class CurrentHoldingSerializer(serializers.Serializer[CurrentPositionPrice]):
    """One current ledger-derived holding with its accepted raw-close price."""

    asset_id = serializers.UUIDField(read_only=True)
    symbol = serializers.CharField(read_only=True)
    quantity = serializers.CharField(read_only=True)
    trade_date = serializers.DateField(read_only=True)
    raw_close = serializers.CharField(read_only=True)
    market_value = serializers.SerializerMethodField()
    stale_trading_sessions = serializers.IntegerField(read_only=True)

    def get_market_value(
        self,
        obj: CurrentPositionPrice,
    ) -> str:
        """Return exact Decimal position market value without float conversion."""
        return str(obj.quantity * obj.raw_close)


class CurrentValuationWarningSerializer(serializers.Serializer[CurrentValuationWarning]):
    """Structured warning emitted by current valuation."""

    code = serializers.ChoiceField(
        choices=[code.value for code in CurrentValuationWarningCode],
        read_only=True,
    )
    message = serializers.CharField(read_only=True)
    asset_id = serializers.UUIDField(read_only=True)
    symbol = serializers.CharField(read_only=True)


class CurrentValuationProvenanceSerializer(serializers.Serializer[CurrentValuationProvenance]):
    """Current raw-close valuation provenance."""

    portfolio_id = serializers.UUIDField(read_only=True)
    benchmark_asset_id = serializers.UUIDField(
        read_only=True,
        allow_null=True,
    )
    provider = serializers.CharField(read_only=True)
    as_of = serializers.DateTimeField(read_only=True)
    retrieved_at = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )
    price_field = serializers.CharField(read_only=True)


class PositionValuationResultSerializer(serializers.Serializer[PositionValuationResult]):
    """Quantitative-engine valuation of one security position."""

    asset_id = serializers.UUIDField(read_only=True)
    quantity = serializers.FloatField(read_only=True)
    valuation_price = serializers.FloatField(read_only=True)
    market_value = serializers.FloatField(read_only=True)


class PortfolioValuationResultSerializer(serializers.Serializer[PortfolioValuationResult]):
    """Quantitative-engine current portfolio valuation."""

    positions = PositionValuationResultSerializer(
        many=True,
        read_only=True,
    )
    security_market_value = serializers.FloatField(read_only=True)
    cash_value = serializers.FloatField(read_only=True)
    total_market_value = serializers.FloatField(read_only=True)


class SecurityAllocationSerializer(serializers.Serializer[SecurityAllocation]):
    """One current security allocation."""

    asset_id = serializers.UUIDField(read_only=True)
    market_value = serializers.FloatField(read_only=True)
    weight = serializers.FloatField(read_only=True)


class PortfolioAllocationResultSerializer(serializers.Serializer[PortfolioAllocationResult]):
    """Current security and cash allocation."""

    positions = SecurityAllocationSerializer(
        many=True,
        read_only=True,
    )
    cash_value = serializers.FloatField(read_only=True)
    cash_weight = serializers.FloatField(read_only=True)
    total_market_value = serializers.FloatField(read_only=True)
    weight_sum = serializers.FloatField(read_only=True)
    weight_sum_tolerance = serializers.FloatField(read_only=True)


class CurrentPortfolioHoldingsSerializer(serializers.Serializer[CurrentPortfolioValuationResult]):
    """Read-only current holdings, value, allocation, and valuation provenance."""

    portfolio_id = serializers.UUIDField(
        source="provenance.portfolio_id",
        read_only=True,
    )
    benchmark_asset_id = serializers.UUIDField(
        source="provenance.benchmark_asset_id",
        read_only=True,
        allow_null=True,
    )
    provider = serializers.CharField(
        source="provenance.provider",
        read_only=True,
    )
    as_of = serializers.DateTimeField(
        source="provenance.as_of",
        read_only=True,
    )
    retrieved_at = serializers.DateTimeField(
        source="provenance.retrieved_at",
        read_only=True,
        allow_null=True,
    )
    price_field = serializers.CharField(
        source="provenance.price_field",
        read_only=True,
    )
    cash_balance = serializers.CharField(
        source="ledger.cash_balance",
        read_only=True,
    )
    transaction_count = serializers.IntegerField(
        source="ledger.transaction_count",
        read_only=True,
    )
    holdings = CurrentHoldingSerializer(
        source="prices",
        many=True,
        read_only=True,
    )
    warnings = CurrentValuationWarningSerializer(
        many=True,
        read_only=True,
    )
    is_complete = serializers.BooleanField(read_only=True)
    valuation = PortfolioValuationResultSerializer(
        read_only=True,
        allow_null=True,
    )
    allocation = PortfolioAllocationResultSerializer(
        read_only=True,
        allow_null=True,
    )


class EngineWarningSerializer(serializers.Serializer[object]):
    """Common representation for quantitative-engine warning objects."""

    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)


class AnnualizedReturnResultSerializer(serializers.Serializer[AnnualizedReturnResult]):
    """CAGR / annualized geometric-return result."""

    value = serializers.FloatField(read_only=True)
    wealth_ratio = serializers.FloatField(read_only=True)
    elapsed_days = serializers.IntegerField(read_only=True)
    elapsed_years = serializers.FloatField(read_only=True)
    is_short_period = serializers.BooleanField(read_only=True)


class SharpeRatioResultSerializer(serializers.Serializer[SharpeRatioResult]):
    """Sharpe result including explicit risk-free assumptions."""

    value = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    observations = serializers.IntegerField(read_only=True)
    risk_free_rate_annual = serializers.FloatField(read_only=True)
    risk_free_rate_daily = serializers.FloatField(read_only=True)
    annualization_factor = serializers.IntegerField(read_only=True)
    warnings = EngineWarningSerializer(
        many=True,
        read_only=True,
    )


class SortinoRatioResultSerializer(serializers.Serializer[SortinoRatioResult]):
    """Sortino result including explicit minimum-acceptable-return assumptions."""

    value = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    observations = serializers.IntegerField(read_only=True)
    minimum_acceptable_return_annual = serializers.FloatField(
        read_only=True,
    )
    minimum_acceptable_return_daily = serializers.FloatField(
        read_only=True,
    )
    downside_deviation = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    annualization_factor = serializers.IntegerField(read_only=True)
    warnings = EngineWarningSerializer(
        many=True,
        read_only=True,
    )


class MaximumDrawdownResultSerializer(serializers.Serializer[MaximumDrawdownResult]):
    """Maximum drawdown and its peak/trough locations."""

    value = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    observations = serializers.IntegerField(read_only=True)
    peak_index = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    trough_index = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    warnings = EngineWarningSerializer(
        many=True,
        read_only=True,
    )


class BetaResultSerializer(serializers.Serializer[BetaResult]):
    """Benchmark beta with aligned observation count and warnings."""

    value = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    observations = serializers.IntegerField(read_only=True)
    warnings = EngineWarningSerializer(
        many=True,
        read_only=True,
    )


class CorrelationResultSerializer(serializers.Serializer[CorrelationResult]):
    """Benchmark Pearson correlation with aligned observation count."""

    value = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    observations = serializers.IntegerField(read_only=True)
    warnings = EngineWarningSerializer(
        many=True,
        read_only=True,
    )


class RollingReturnObservationSerializer(serializers.Serializer[RollingReturnObservation]):
    """One server-calculated trailing cumulative return endpoint."""

    period_end = serializers.DateField(read_only=True)
    value = serializers.FloatField(read_only=True)


class ConcentrationResultSerializer(serializers.Serializer[ConcentrationResult]):
    """Canonical current portfolio concentration measures."""

    largest_position_weight = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    herfindahl_hirschman_index = serializers.FloatField(read_only=True)
    security_position_count = serializers.IntegerField(read_only=True)
    cash_weight = serializers.FloatField(read_only=True)
    largest_position_includes_cash = serializers.BooleanField(read_only=True)
    hhi_includes_cash = serializers.BooleanField(read_only=True)
    long_only = serializers.BooleanField(read_only=True)
    weight_sum_tolerance = serializers.FloatField(read_only=True)


class AnalyticalResultProvenanceSerializer(serializers.Serializer[AnalyticalResultProvenance]):
    """Public analytical provenance envelope required by Section 8.8."""

    engine_version = serializers.CharField(read_only=True)
    as_of_date = serializers.DateField(read_only=True)
    period_start = serializers.DateField(read_only=True)
    period_end = serializers.DateField(read_only=True)
    data_source = serializers.CharField(read_only=True)
    price_field = serializers.CharField(read_only=True)
    annualization_factor = serializers.FloatField(read_only=True)
    benchmark = serializers.CharField(
        read_only=True,
        allow_null=True,
    )
    assumptions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class PortfolioAnalyticsWarningSerializer(serializers.Serializer[PortfolioAnalyticsWarning]):
    """Structured application-level analytical warning."""

    code = serializers.ChoiceField(
        choices=[code.value for code in PortfolioAnalyticsWarningCode],
        read_only=True,
    )
    message = serializers.CharField(read_only=True)
    observations = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )


class PortfolioAnalyticsResultSerializer(serializers.Serializer[PortfolioAnalyticsResult]):
    """Complete owned-portfolio analytical response contract."""

    portfolio_id = serializers.UUIDField(read_only=True)
    observations = serializers.IntegerField(read_only=True)
    benchmark_observations = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    cumulative_return = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    cagr = AnnualizedReturnResultSerializer(
        read_only=True,
        allow_null=True,
    )
    annualized_volatility = serializers.FloatField(
        read_only=True,
        allow_null=True,
    )
    sharpe = SharpeRatioResultSerializer(
        read_only=True,
        allow_null=True,
    )
    sortino = SortinoRatioResultSerializer(
        read_only=True,
        allow_null=True,
    )
    maximum_drawdown = MaximumDrawdownResultSerializer(
        read_only=True,
        allow_null=True,
    )
    beta = BetaResultSerializer(
        read_only=True,
        allow_null=True,
    )
    benchmark_correlation = CorrelationResultSerializer(
        read_only=True,
        allow_null=True,
    )
    current_allocation = PortfolioAllocationResultSerializer(
        read_only=True,
        allow_null=True,
    )
    concentration = ConcentrationResultSerializer(
        read_only=True,
        allow_null=True,
    )
    rolling_return_window = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    rolling_returns = RollingReturnObservationSerializer(
        many=True,
        read_only=True,
    )
    provenance = AnalyticalResultProvenanceSerializer(read_only=True)
    warnings = PortfolioAnalyticsWarningSerializer(
        many=True,
        read_only=True,
    )
