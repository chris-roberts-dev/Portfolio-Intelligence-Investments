"""Integration coverage for P0 dashboard accounting-summary composition."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from apps.accounts.models import User
from apps.portfolios.models import Portfolio
from apps.portfolios.services import dashboard_summary
from apps.portfolios.services.book_accounting import (
    BookCostPosition,
    PortfolioBookAccountingResult,
)
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentPositionPrice,
    CurrentValuationProvenance,
    CurrentValuationWarning,
    CurrentValuationWarningCode,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)
from apps.portfolios.services.dashboard_summary import (
    PortfolioSummaryUnavailableReason,
    build_owned_portfolio_dashboard_summary,
)
from apps.portfolios.services.ledger import (
    LedgerReplayResult,
    PositionQuantity,
)

PORTFOLIO_ID = UUID("00000000-0000-0000-0000-000000001001")
ASSET_ID = UUID("00000000-0000-0000-0000-000000001011")
CALCULATED_AT = datetime(2026, 9, 15, 16, tzinfo=UTC)


def ledger() -> LedgerReplayResult:
    return LedgerReplayResult(
        portfolio_id=PORTFOLIO_ID,
        as_of=CALCULATED_AT,
        cash_balance=Decimal("800"),
        positions=(
            PositionQuantity(
                asset_id=ASSET_ID,
                quantity=Decimal("2"),
            ),
        ),
        cash_flows=(),
        net_external_cash_flow=Decimal("1000"),
        net_internal_cash_flow=Decimal("-200"),
        transaction_count=2,
    )


def accounting() -> PortfolioBookAccountingResult:
    return PortfolioBookAccountingResult(
        portfolio_id=PORTFOLIO_ID,
        as_of=CALCULATED_AT,
        positions=(
            BookCostPosition(
                asset_id=ASSET_ID,
                quantity=Decimal("2"),
                cost_basis=Decimal("150"),
                average_unit_cost=Decimal("75"),
            ),
        ),
        total_open_cost_basis=Decimal("150"),
        net_contributions=Decimal("1000"),
        selected_period_realized_gain_loss=Decimal("30"),
        selected_period_income=Decimal("10"),
        selected_period_unavailable_reason=None,
    )


@pytest.mark.django_db
def test_complete_summary_preserves_exact_decimal_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="summary-service@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Summary Portfolio",
    )
    current = CurrentPortfolioValuationResult(
        ledger=ledger(),
        provenance=CurrentValuationProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=None,
            provider="mock",
            as_of=CALCULATED_AT,
            retrieved_at=CALCULATED_AT,
            price_field="close",
        ),
        prices=(
            CurrentPositionPrice(
                asset_id=ASSET_ID,
                symbol="AAA",
                quantity=Decimal("2"),
                trade_date=date(2026, 9, 15),
                raw_close=Decimal("100"),
                stale_trading_sessions=0,
            ),
        ),
        warnings=(),
        is_complete=True,
        valuation=None,
        allocation=None,
    )

    monkeypatch.setattr(
        dashboard_summary,
        "value_owned_portfolio",
        lambda **_kwargs: current,
    )
    monkeypatch.setattr(
        dashboard_summary,
        "calculate_portfolio_book_accounting",
        lambda *_args, **_kwargs: accounting(),
    )

    result = build_owned_portfolio_dashboard_summary(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        requested_start=date(2026, 9, 1),
        requested_end=date(2026, 9, 16),
        provider_name="mock",
        resolver=object(),  # type: ignore[arg-type]
        provider=object(),  # type: ignore[arg-type]
        trading_calendar=object(),  # type: ignore[arg-type]
        calculated_at=CALCULATED_AT,
    )

    assert result.metrics.total_market_value == Decimal("1000")
    assert result.metrics.net_contributions == Decimal("1000")
    assert result.metrics.cost_basis == Decimal("150")
    assert result.metrics.cash_balance == Decimal("800")
    assert result.metrics.cash_percentage == Decimal("0.8")
    assert result.metrics.unrealized_gain_loss == Decimal("50")
    assert result.metrics.selected_period_realized_gain_loss == Decimal("30")
    assert result.metrics.selected_period_income_received == Decimal("10")
    assert result.data_quality is PerformanceDataQualityState.CURRENT
    assert result.provenance.accounting_method == ("WEIGHTED_AVERAGE_BOOK_COST_V1")


@pytest.mark.django_db
def test_incomplete_current_price_does_not_erase_valid_ledger_accounting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User.objects.create_user(
        email="summary-incomplete@example.com",
        password="test-password-123",
    )
    Portfolio.objects.create(
        id=PORTFOLIO_ID,
        user=user,
        name="Summary Portfolio",
    )
    current = CurrentPortfolioValuationResult(
        ledger=ledger(),
        provenance=CurrentValuationProvenance(
            portfolio_id=PORTFOLIO_ID,
            benchmark_asset_id=None,
            provider="mock",
            as_of=CALCULATED_AT,
            retrieved_at=CALCULATED_AT,
            price_field="close",
        ),
        prices=(),
        warnings=(
            CurrentValuationWarning(
                code=CurrentValuationWarningCode.PRICE_NO_DATA,
                message="No current price.",
                asset_id=ASSET_ID,
                symbol="AAA",
            ),
        ),
        is_complete=False,
        valuation=None,
        allocation=None,
    )

    monkeypatch.setattr(
        dashboard_summary,
        "value_owned_portfolio",
        lambda **_kwargs: current,
    )
    monkeypatch.setattr(
        dashboard_summary,
        "calculate_portfolio_book_accounting",
        lambda *_args, **_kwargs: accounting(),
    )

    result = build_owned_portfolio_dashboard_summary(
        user=user,
        portfolio_id=PORTFOLIO_ID,
        requested_start=date(2026, 9, 1),
        requested_end=date(2026, 9, 16),
        provider_name="mock",
        resolver=object(),  # type: ignore[arg-type]
        provider=object(),  # type: ignore[arg-type]
        trading_calendar=object(),  # type: ignore[arg-type]
        calculated_at=CALCULATED_AT,
    )

    assert result.metrics.total_market_value is None
    assert (
        result.metrics.total_market_value_unavailable_reason
        is PortfolioSummaryUnavailableReason.CURRENT_VALUATION_INCOMPLETE
    )
    assert result.metrics.cash_percentage is None
    assert result.metrics.unrealized_gain_loss is None

    assert result.metrics.cost_basis == Decimal("150")
    assert result.metrics.net_contributions == Decimal("1000")
    assert result.metrics.selected_period_realized_gain_loss == Decimal("30")
    assert result.metrics.selected_period_income_received == Decimal("10")
    assert result.data_quality is PerformanceDataQualityState.PARTIAL
