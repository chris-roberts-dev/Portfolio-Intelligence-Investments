"""Focused tests for explicit portfolio and analytics DRF transport contracts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from apps.portfolios.api.serializers import (
    CurrentPortfolioHoldingsSerializer,
    PortfolioAnalyticsResultSerializer,
    PortfolioSummarySerializer,
)
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
from apps.portfolios.services.ledger import (
    LedgerReplayResult,
    PositionQuantity,
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

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000000101")
ASSET_ID = UUID("00000000-0000-0000-0000-000000000201")
BENCHMARK_ID = UUID("00000000-0000-0000-0000-000000000301")
AS_OF = datetime(2026, 9, 15, 21, tzinfo=UTC)
RETRIEVED_AT = datetime(2026, 9, 15, 20, 30, tzinfo=UTC)


def test_portfolio_summary_serializer_uses_explicit_public_fields() -> None:
    created_at = datetime(2026, 1, 2, 12, tzinfo=UTC)
    updated_at = datetime(2026, 2, 3, 14, tzinfo=UTC)
    portfolio = SimpleNamespace(
        id=PORTFOLIO_ID,
        name="Long-Term Portfolio",
        base_currency="USD",
        benchmark_asset_id=BENCHMARK_ID,
        ledger_inception_at=None,
        created_at=created_at,
        updated_at=updated_at,
    )

    data = PortfolioSummarySerializer(portfolio).data

    assert data == {
        "id": str(PORTFOLIO_ID),
        "name": "Long-Term Portfolio",
        "base_currency": "USD",
        "benchmark_asset_id": str(BENCHMARK_ID),
        "ledger_inception_at": None,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
    }


def test_current_holdings_serializer_preserves_decimal_strings_and_provenance() -> None:
    quantity = Decimal("2.000000000000")
    raw_close = Decimal("100.12500000")
    cash_balance = Decimal("799.75000000")
    market_value = quantity * raw_close

    ledger = LedgerReplayResult(
        portfolio_id=PORTFOLIO_ID,
        as_of=AS_OF,
        cash_balance=cash_balance,
        positions=(
            PositionQuantity(
                asset_id=ASSET_ID,
                quantity=quantity,
            ),
        ),
        cash_flows=(),
        net_external_cash_flow=Decimal("1000.00000000"),
        net_internal_cash_flow=Decimal("-200.25000000"),
        transaction_count=2,
    )
    price = CurrentPositionPrice(
        asset_id=ASSET_ID,
        symbol="AAPL",
        quantity=quantity,
        trade_date=date(2026, 9, 15),
        raw_close=raw_close,
        stale_trading_sessions=0,
    )
    valuation = PortfolioValuationResult(
        positions=(
            PositionValuationResult(
                asset_id=ASSET_ID,
                quantity=2.0,
                valuation_price=100.125,
                market_value=200.25,
            ),
        ),
        security_market_value=200.25,
        cash_value=799.75,
        total_market_value=1000.0,
    )
    allocation = PortfolioAllocationResult(
        positions=(
            SecurityAllocation(
                asset_id=ASSET_ID,
                market_value=200.25,
                weight=0.20025,
            ),
        ),
        cash_value=799.75,
        cash_weight=0.79975,
        total_market_value=1000.0,
        weight_sum=1.0,
        weight_sum_tolerance=1e-8,
    )
    result = CurrentPortfolioValuationResult(
        ledger=ledger,
        provenance=CurrentValuationProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=BENCHMARK_ID,
            provider="mock",
            as_of=AS_OF,
            retrieved_at=RETRIEVED_AT,
            price_field="close",
        ),
        prices=(price,),
        warnings=(
            CurrentValuationWarning(
                code=CurrentValuationWarningCode.STALE_PRICE_USED,
                message="Test warning.",
                asset_id=ASSET_ID,
                symbol="AAPL",
            ),
        ),
        is_complete=True,
        valuation=valuation,
        allocation=allocation,
    )

    data = CurrentPortfolioHoldingsSerializer(result).data

    assert data["portfolio_id"] == str(PORTFOLIO_ID)
    assert data["benchmark_asset_id"] == str(BENCHMARK_ID)
    assert data["provider"] == "mock"
    assert data["price_field"] == "close"
    assert data["cash_balance"] == str(cash_balance)
    assert data["transaction_count"] == 2
    assert data["is_complete"] is True

    holding = data["holdings"][0]
    assert holding["asset_id"] == str(ASSET_ID)
    assert holding["symbol"] == "AAPL"
    assert holding["quantity"] == str(quantity)
    assert holding["raw_close"] == str(raw_close)
    assert holding["market_value"] == str(market_value)
    assert holding["stale_trading_sessions"] == 0

    assert data["warnings"][0]["code"] == "STALE_PRICE_USED"
    assert data["valuation"]["total_market_value"] == pytest.approx(1000.0)
    assert data["allocation"]["cash_weight"] == pytest.approx(0.79975)


def test_analytics_serializer_preserves_metrics_assumptions_and_warning_structure() -> None:
    provenance = AnalyticalResultProvenance(
        as_of_date=date(2026, 9, 15),
        period_start=date(2026, 1, 2),
        period_end=date(2026, 9, 15),
        data_source="mock",
        price_field="adjusted_close",
        annualization_factor=252.0,
        benchmark="SPY",
        assumptions=(
            "historical returns use adjusted_close",
            "risk_free_rate_annual=0.02",
        ),
        warnings=("One source warning.",),
    )
    allocation = PortfolioAllocationResult(
        positions=(
            SecurityAllocation(
                asset_id=ASSET_ID,
                market_value=700.0,
                weight=0.7,
            ),
        ),
        cash_value=300.0,
        cash_weight=0.3,
        total_market_value=1000.0,
        weight_sum=1.0,
        weight_sum_tolerance=1e-8,
    )
    result = PortfolioAnalyticsResult(
        portfolio_id=PORTFOLIO_ID,
        observations=120,
        benchmark_observations=118,
        cumulative_return=0.123456789012345,
        cagr=AnnualizedReturnResult(
            value=0.180123456789,
            wealth_ratio=1.123456789012345,
            elapsed_days=256,
            elapsed_years=0.700904194,
            is_short_period=True,
        ),
        annualized_volatility=0.20123456789,
        sharpe=SharpeRatioResult(
            value=0.8123456789,
            observations=120,
            risk_free_rate_annual=0.02,
            risk_free_rate_daily=0.000078583,
            annualization_factor=252,
        ),
        sortino=SortinoRatioResult(
            value=1.1123456789,
            observations=120,
            minimum_acceptable_return_annual=0.0,
            minimum_acceptable_return_daily=0.0,
            downside_deviation=0.007123456789,
            annualization_factor=252,
        ),
        maximum_drawdown=MaximumDrawdownResult(
            value=-0.1423456789,
            observations=120,
            peak_index=20,
            trough_index=47,
        ),
        beta=BetaResult(
            value=0.923456789,
            observations=118,
        ),
        benchmark_correlation=CorrelationResult(
            value=0.87654321,
            observations=118,
        ),
        current_allocation=allocation,
        concentration=ConcentrationResult(
            largest_position_weight=0.7,
            herfindahl_hirschman_index=0.49,
            security_position_count=1,
            cash_weight=0.3,
            largest_position_includes_cash=False,
            hhi_includes_cash=False,
            long_only=True,
            weight_sum_tolerance=1e-8,
        ),
        provenance=provenance,
        rolling_return_window=21,
        rolling_returns=(
            RollingReturnObservation(
                period_end=date(2026, 8, 31),
                value=0.04123456789,
            ),
            RollingReturnObservation(
                period_end=date(2026, 9, 15),
                value=0.05123456789,
            ),
        ),
        warnings=(
            PortfolioAnalyticsWarning(
                code=PortfolioAnalyticsWarningCode.SOURCE_WARNING,
                message="One source warning.",
                observations=120,
            ),
        ),
    )

    data = PortfolioAnalyticsResultSerializer(result).data

    assert data["portfolio_id"] == str(PORTFOLIO_ID)
    assert data["observations"] == 120
    assert data["benchmark_observations"] == 118
    assert data["cumulative_return"] == pytest.approx(0.123456789012345)

    assert data["cagr"]["value"] == pytest.approx(0.180123456789)
    assert data["sharpe"]["value"] == pytest.approx(0.8123456789)
    assert data["sortino"]["value"] == pytest.approx(1.1123456789)
    assert data["maximum_drawdown"]["value"] == pytest.approx(-0.1423456789)
    assert data["beta"]["value"] == pytest.approx(0.923456789)
    assert data["benchmark_correlation"]["value"] == pytest.approx(0.87654321)
    assert data["benchmark_correlation"]["observations"] == 118
    assert data["rolling_return_window"] == 21
    assert data["rolling_returns"] == [
        {
            "period_end": "2026-08-31",
            "value": pytest.approx(0.04123456789),
        },
        {
            "period_end": "2026-09-15",
            "value": pytest.approx(0.05123456789),
        },
    ]

    assert data["current_allocation"]["positions"][0]["weight"] == pytest.approx(0.7)
    assert data["concentration"]["herfindahl_hirschman_index"] == pytest.approx(0.49)

    assert data["provenance"]["data_source"] == "mock"
    assert data["provenance"]["price_field"] == "adjusted_close"
    assert data["provenance"]["benchmark"] == "SPY"
    assert data["provenance"]["annualization_factor"] == pytest.approx(252.0)
    assert data["provenance"]["assumptions"] == [
        "historical returns use adjusted_close",
        "risk_free_rate_annual=0.02",
    ]
    assert data["provenance"]["warnings"] == ["One source warning."]

    assert data["warnings"] == [
        {
            "code": "SOURCE_WARNING",
            "message": "One source warning.",
            "observations": 120,
        }
    ]


def test_analytics_serializer_represents_undefined_metrics_as_null() -> None:
    result = PortfolioAnalyticsResult(
        portfolio_id=PORTFOLIO_ID,
        observations=5,
        benchmark_observations=None,
        cumulative_return=None,
        cagr=None,
        annualized_volatility=None,
        sharpe=None,
        sortino=None,
        maximum_drawdown=None,
        beta=None,
        current_allocation=None,
        concentration=None,
        provenance=AnalyticalResultProvenance(
            as_of_date=date(2026, 9, 15),
            period_start=date(2026, 9, 10),
            period_end=date(2026, 9, 15),
            data_source="mock",
            price_field="adjusted_close",
            annualization_factor=252.0,
            benchmark=None,
            warnings=("Insufficient history.",),
        ),
        warnings=(
            PortfolioAnalyticsWarning(
                code=PortfolioAnalyticsWarningCode.INSUFFICIENT_HISTORY,
                message="Insufficient history.",
                observations=5,
            ),
        ),
    )

    data = PortfolioAnalyticsResultSerializer(result).data

    assert data["benchmark_observations"] is None
    assert data["cumulative_return"] is None
    assert data["cagr"] is None
    assert data["annualized_volatility"] is None
    assert data["sharpe"] is None
    assert data["sortino"] is None
    assert data["maximum_drawdown"] is None
    assert data["beta"] is None
    assert data["benchmark_correlation"] is None
    assert data["rolling_return_window"] is None
    assert data["rolling_returns"] == []
    assert data["current_allocation"] is None
    assert data["concentration"] is None
    assert data["warnings"][0]["code"] == "INSUFFICIENT_HISTORY"
