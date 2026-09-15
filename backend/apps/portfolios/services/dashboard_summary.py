"""P0 display-ready portfolio accounting summary.

Ledger-derived accounting remains Decimal-based. Current market valuation uses
the existing provider-neutral raw-close valuation service.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
from apps.portfolios.services.book_accounting import (
    ANALYTICAL_BOOK_COST_METHOD,
    BOOK_ACCOUNTING_ASSUMPTIONS,
    BookAccountingUnavailableReason,
    PortfolioBookAccountingResult,
    calculate_portfolio_book_accounting,
)
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentValuationWarningCode,
    MarketBarQueryExecutor,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)

ZERO = Decimal("0")


class DashboardPortfolioSummaryError(ValueError):
    """Raised when dashboard summary inputs are internally inconsistent."""


class PortfolioSummaryUnavailableReason(StrEnum):
    """Stable reasons a summary metric is explicitly unavailable."""

    CURRENT_VALUATION_INCOMPLETE = "CURRENT_VALUATION_INCOMPLETE"
    TOTAL_MARKET_VALUE_NON_POSITIVE = "TOTAL_MARKET_VALUE_NON_POSITIVE"
    SELECTED_PERIOD_NOT_STARTED = "SELECTED_PERIOD_NOT_STARTED"


@dataclass(frozen=True, slots=True)
class DashboardPortfolioSummaryMetrics:
    """Exact accounting values required by the P0 portfolio summary card."""

    total_market_value: Decimal | None
    total_market_value_unavailable_reason: PortfolioSummaryUnavailableReason | None
    net_contributions: Decimal
    cost_basis: Decimal
    cash_balance: Decimal
    cash_percentage: Decimal | None
    cash_percentage_unavailable_reason: PortfolioSummaryUnavailableReason | None
    unrealized_gain_loss: Decimal | None
    unrealized_gain_loss_unavailable_reason: PortfolioSummaryUnavailableReason | None
    selected_period_realized_gain_loss: Decimal | None
    selected_period_realized_gain_loss_unavailable_reason: PortfolioSummaryUnavailableReason | None
    selected_period_income_received: Decimal | None
    selected_period_income_unavailable_reason: PortfolioSummaryUnavailableReason | None


@dataclass(frozen=True, slots=True)
class DashboardPortfolioSummaryProvenance:
    """Accounting, period, and market-data provenance."""

    portfolio_id: UUID
    base_currency: str
    provider: str
    requested_start: date
    requested_end_exclusive: date
    ledger_as_of: datetime
    current_price_data_as_of: datetime | None
    calculated_at: datetime
    current_price_field: str
    accounting_method: str
    accounting_assumptions: tuple[str, ...]
    selected_period_transaction_timezone: str
    net_contributions_scope: str
    selected_period_accounting_scope: str


@dataclass(frozen=True, slots=True)
class DashboardPortfolioSummaryResult:
    """Complete P0 dashboard portfolio summary response."""

    metrics: DashboardPortfolioSummaryMetrics
    data_quality: PerformanceDataQualityState
    warnings: tuple[str, ...]
    provenance: DashboardPortfolioSummaryProvenance


def build_owned_portfolio_dashboard_summary(
    *,
    user: User,
    portfolio_id: UUID,
    requested_start: date,
    requested_end: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    calculated_at: datetime,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardPortfolioSummaryResult:
    """Build current accounting summary plus selected-period ledger metrics."""
    if requested_start >= requested_end:
        raise DashboardPortfolioSummaryError("requested_start must be before requested_end")

    if timezone.is_naive(calculated_at):
        raise DashboardPortfolioSummaryError("calculated_at must be timezone-aware")

    portfolio = Portfolio.objects.owned_by(user).get(id=portfolio_id)
    period_start = datetime.combine(
        requested_start,
        time.min,
        tzinfo=UTC,
    )
    period_end_exclusive = datetime.combine(
        requested_end,
        time.min,
        tzinfo=UTC,
    )

    current = value_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        as_of=calculated_at,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
    )
    accounting = calculate_portfolio_book_accounting(
        portfolio,
        as_of=calculated_at,
        period_start=period_start,
        period_end_exclusive=period_end_exclusive,
    )

    _validate_ledger_alignment(
        current=current,
        accounting=accounting,
    )

    security_market_value = _security_market_value(current)
    total_market_value = (
        current.ledger.cash_balance + security_market_value
        if security_market_value is not None
        else None
    )

    if total_market_value is None:
        total_reason = PortfolioSummaryUnavailableReason.CURRENT_VALUATION_INCOMPLETE
        cash_percentage = None
        cash_percentage_reason = total_reason
        unrealized_gain_loss = None
        unrealized_reason = total_reason
    else:
        total_reason = None
        assert security_market_value is not None

        if total_market_value > ZERO:
            cash_percentage = current.ledger.cash_balance / total_market_value
            cash_percentage_reason = None
        else:
            cash_percentage = None
            cash_percentage_reason = (
                PortfolioSummaryUnavailableReason.TOTAL_MARKET_VALUE_NON_POSITIVE
            )

        unrealized_gain_loss = security_market_value - accounting.total_open_cost_basis
        unrealized_reason = None

    selected_reason = _selected_period_unavailable_reason(accounting)

    return DashboardPortfolioSummaryResult(
        metrics=DashboardPortfolioSummaryMetrics(
            total_market_value=total_market_value,
            total_market_value_unavailable_reason=total_reason,
            net_contributions=accounting.net_contributions,
            cost_basis=accounting.total_open_cost_basis,
            cash_balance=current.ledger.cash_balance,
            cash_percentage=cash_percentage,
            cash_percentage_unavailable_reason=cash_percentage_reason,
            unrealized_gain_loss=unrealized_gain_loss,
            unrealized_gain_loss_unavailable_reason=unrealized_reason,
            selected_period_realized_gain_loss=(accounting.selected_period_realized_gain_loss),
            selected_period_realized_gain_loss_unavailable_reason=(selected_reason),
            selected_period_income_received=accounting.selected_period_income,
            selected_period_income_unavailable_reason=selected_reason,
        ),
        data_quality=_data_quality(current),
        warnings=tuple(warning.message for warning in current.warnings),
        provenance=DashboardPortfolioSummaryProvenance(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            provider=current.provenance.provider,
            requested_start=requested_start,
            requested_end_exclusive=requested_end,
            ledger_as_of=calculated_at,
            current_price_data_as_of=current.provenance.retrieved_at,
            calculated_at=calculated_at,
            current_price_field="close",
            accounting_method=ANALYTICAL_BOOK_COST_METHOD,
            accounting_assumptions=BOOK_ACCOUNTING_ASSUMPTIONS,
            selected_period_transaction_timezone="UTC",
            net_contributions_scope="LIFETIME_THROUGH_LEDGER_AS_OF",
            selected_period_accounting_scope=("REQUESTED_RANGE_INTERSECTED_WITH_LEDGER_AS_OF"),
        ),
    )


def _validate_ledger_alignment(
    *,
    current: CurrentPortfolioValuationResult,
    accounting: PortfolioBookAccountingResult,
) -> None:
    if current.ledger.portfolio_id != accounting.portfolio_id:
        raise DashboardPortfolioSummaryError(
            "Current valuation and book accounting reference different portfolios."
        )

    ledger_quantities = {
        position.asset_id: position.quantity for position in current.ledger.positions
    }
    accounting_quantities = {
        position.asset_id: position.quantity for position in accounting.positions
    }

    if ledger_quantities != accounting_quantities:
        raise DashboardPortfolioSummaryError(
            "Ledger quantities and analytical book-accounting quantities disagree."
        )

    if current.ledger.net_external_cash_flow != accounting.net_contributions:
        raise DashboardPortfolioSummaryError(
            "Ledger external cash flow and net contributions disagree."
        )


def _security_market_value(
    current: CurrentPortfolioValuationResult,
) -> Decimal | None:
    if not current.is_complete:
        return None

    return sum(
        (price.quantity * price.raw_close for price in current.prices),
        ZERO,
    )


def _selected_period_unavailable_reason(
    accounting: PortfolioBookAccountingResult,
) -> PortfolioSummaryUnavailableReason | None:
    if (
        accounting.selected_period_unavailable_reason
        is BookAccountingUnavailableReason.SELECTED_PERIOD_NOT_STARTED
    ):
        return PortfolioSummaryUnavailableReason.SELECTED_PERIOD_NOT_STARTED

    return None


def _data_quality(
    current: CurrentPortfolioValuationResult,
) -> PerformanceDataQualityState:
    if not current.is_complete:
        return PerformanceDataQualityState.PARTIAL

    if any(
        warning.code is CurrentValuationWarningCode.STALE_PRICE_USED for warning in current.warnings
    ):
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT
