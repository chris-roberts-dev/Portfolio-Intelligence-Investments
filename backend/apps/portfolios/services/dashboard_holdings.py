"""Display-ready owned-portfolio holdings for dashboard consumers.

Current quantities and cash come from ledger replay through the existing current
valuation service. Current valuation uses raw close; selected-period movement
and sparklines use adjusted close. Missing historical observations remain
explicit gaps and are never interpolated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.market_data.contracts import (
    MarketBarStatus,
    MarketBarSymbolResult,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
from apps.portfolios.services.current_valuation import (
    CurrentPortfolioValuationResult,
    CurrentPositionPrice,
    MarketBarQueryExecutor,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)
from portfolio_engine.performance.returns import simple_returns


class DashboardHoldingsError(ValueError):
    """Raised when dashboard holdings cannot be assembled safely."""


class HoldingMetricUnavailableReason(StrEnum):
    """Stable reasons a requested holding metric is explicitly unavailable."""

    CURRENT_PRICE_UNAVAILABLE = "CURRENT_PRICE_UNAVAILABLE"
    PERIOD_HISTORY_UNAVAILABLE = "PERIOD_HISTORY_UNAVAILABLE"
    PERIOD_START_PRICE_UNAVAILABLE = "PERIOD_START_PRICE_UNAVAILABLE"
    PERIOD_END_PRICE_UNAVAILABLE = "PERIOD_END_PRICE_UNAVAILABLE"
    CURRENT_ALLOCATION_UNAVAILABLE = "CURRENT_ALLOCATION_UNAVAILABLE"
    CONTRIBUTION_NOT_CALCULATED = "CONTRIBUTION_NOT_CALCULATED"


class DashboardHoldingWarningCode(StrEnum):
    """Stable warning codes for holding-level market-data diagnostics."""

    CURRENT_PRICE_WARNING = "CURRENT_PRICE_WARNING"
    PERIOD_NOT_FOUND = "PERIOD_NOT_FOUND"
    PERIOD_NO_DATA = "PERIOD_NO_DATA"
    PERIOD_PROVIDER_FAILED = "PERIOD_PROVIDER_FAILED"
    PERIOD_PROVIDER_WARNING = "PERIOD_PROVIDER_WARNING"
    PERIOD_MISSING_OBSERVATION = "PERIOD_MISSING_OBSERVATION"


@dataclass(frozen=True, slots=True)
class HoldingSparklinePoint:
    """One exact-date adjusted-close sparkline point."""

    observation_date: date
    adjusted_close: Decimal | None


@dataclass(frozen=True, slots=True)
class DashboardHoldingWarning:
    """One structured warning for a dashboard holding."""

    code: DashboardHoldingWarningCode
    message: str
    asset_id: UUID
    symbol: str
    observation_date: date | None = None


@dataclass(frozen=True, slots=True)
class DashboardHolding:
    """One dashboard-ready current holding with selected-period movement."""

    asset_id: UUID
    symbol: str
    name: str
    asset_type: str
    currency: str
    quantity: Decimal
    current_price: Decimal | None
    current_price_date: date | None
    current_price_retrieved_at: datetime | None
    stale_trading_sessions: int | None
    market_value: Decimal | None
    weight: float | None
    weight_unavailable_reason: HoldingMetricUnavailableReason | None
    selected_period_return: float | None
    selected_period_return_unavailable_reason: HoldingMetricUnavailableReason | None
    contribution_to_return: float | None
    contribution_unavailable_reason: HoldingMetricUnavailableReason | None
    sparkline: tuple[HoldingSparklinePoint, ...]
    data_quality: PerformanceDataQualityState
    warnings: tuple[DashboardHoldingWarning, ...]


@dataclass(frozen=True, slots=True)
class DashboardHoldingsProvenance:
    """Market-data and requested/effective period provenance for holdings."""

    portfolio_id: UUID
    base_currency: str
    provider: str
    requested_start: date
    requested_end_exclusive: date
    effective_start: date
    effective_end_exclusive: date
    current_price_as_of: datetime | None
    period_data_as_of: datetime | None
    calculated_at: datetime
    current_price_field: str
    period_price_field: str


@dataclass(frozen=True, slots=True)
class DashboardHoldingsResult:
    """Display-ready current holdings and selected-period movement result."""

    holdings: tuple[DashboardHolding, ...]
    data_quality: PerformanceDataQualityState
    warnings: tuple[DashboardHoldingWarning, ...]
    provenance: DashboardHoldingsProvenance


def build_owned_portfolio_dashboard_holdings(
    *,
    user: User,
    portfolio_id: UUID,
    observation_dates: tuple[date, ...],
    requested_start: date,
    requested_end: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    calculated_at: datetime,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardHoldingsResult:
    """Build current holdings with exact-date selected-period price history."""
    _validate_request_context(
        observation_dates=observation_dates,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
    )
    portfolio = Portfolio.objects.owned_by(user).get(id=portfolio_id)
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
    assets = _assets_for_current_holdings(current)

    if not current.ledger.positions:
        return DashboardHoldingsResult(
            holdings=(),
            data_quality=PerformanceDataQualityState.CURRENT,
            warnings=(),
            provenance=_provenance(
                portfolio=portfolio,
                current=current,
                requested_start=requested_start,
                requested_end=requested_end,
                observation_dates=observation_dates,
                period_data_as_of=None,
                calculated_at=calculated_at,
            ),
        )

    history_batch = executor(
        normalize_market_bar_query(
            tuple(assets[position.asset_id].symbol for position in current.ledger.positions),
            start=observation_dates[0],
            end=observation_dates[-1] + timedelta(days=1),
            provider=current.provenance.provider,
        ),
        resolver=resolver,
        provider=provider,
    )

    if history_batch.meta.provider != current.provenance.provider:
        raise DashboardHoldingsError(
            "Current and selected-period holdings data must use one provider."
        )

    history_by_symbol = {result.symbol: result for result in history_batch.results}
    current_price_by_asset = {price.asset_id: price for price in current.prices}
    weight_by_asset = _weight_by_asset(current)
    current_warning_by_asset = _current_warnings_by_asset(current)

    holdings = tuple(
        _build_holding(
            asset=assets[position.asset_id],
            quantity=position.quantity,
            current_price=current_price_by_asset.get(position.asset_id),
            current_retrieved_at=current.provenance.retrieved_at,
            current_warning_messages=current_warning_by_asset.get(
                position.asset_id,
                (),
            ),
            weight=weight_by_asset.get(position.asset_id),
            history_result=history_by_symbol.get(assets[position.asset_id].symbol),
            observation_dates=observation_dates,
        )
        for position in current.ledger.positions
    )
    warnings = tuple(warning for holding in holdings for warning in holding.warnings)

    return DashboardHoldingsResult(
        holdings=holdings,
        data_quality=_overall_quality(holdings),
        warnings=warnings,
        provenance=_provenance(
            portfolio=portfolio,
            current=current,
            requested_start=requested_start,
            requested_end=requested_end,
            observation_dates=observation_dates,
            period_data_as_of=history_batch.meta.retrieved_at,
            calculated_at=calculated_at,
        ),
    )


def _validate_request_context(
    *,
    observation_dates: tuple[date, ...],
    requested_start: date,
    requested_end: date,
    calculated_at: datetime,
) -> None:
    if requested_start >= requested_end:
        raise DashboardHoldingsError("requested_start must be before requested_end")

    if len(observation_dates) < 2:
        raise DashboardHoldingsError("dashboard holdings require at least two trading sessions")

    if tuple(sorted(set(observation_dates))) != observation_dates:
        raise DashboardHoldingsError("observation_dates must be unique and strictly ascending")

    if observation_dates[0] < requested_start or observation_dates[-1] >= requested_end:
        raise DashboardHoldingsError("observation dates must remain inside the requested range")

    if timezone.is_naive(calculated_at):
        raise DashboardHoldingsError("calculated_at must be timezone-aware")


def _assets_for_current_holdings(
    current: CurrentPortfolioValuationResult,
) -> dict[UUID, Asset]:
    asset_ids = tuple(position.asset_id for position in current.ledger.positions)
    assets = Asset.objects.in_bulk(asset_ids)
    missing = tuple(asset_id for asset_id in asset_ids if asset_id not in assets)

    if missing:
        raise DashboardHoldingsError(f"Current ledger references unknown asset IDs: {missing!r}.")

    return assets


def _weight_by_asset(
    current: CurrentPortfolioValuationResult,
) -> dict[UUID, float]:
    if current.allocation is None:
        return {}

    return {allocation.asset_id: allocation.weight for allocation in current.allocation.positions}


def _current_warnings_by_asset(
    current: CurrentPortfolioValuationResult,
) -> dict[UUID, tuple[str, ...]]:
    warnings: dict[UUID, list[str]] = {}

    for warning in current.warnings:
        warnings.setdefault(
            warning.asset_id,
            [],
        ).append(warning.message)

    return {asset_id: tuple(messages) for asset_id, messages in warnings.items()}


def _build_holding(
    *,
    asset: Asset,
    quantity: Decimal,
    current_price: CurrentPositionPrice | None,
    current_retrieved_at: datetime | None,
    current_warning_messages: tuple[str, ...],
    weight: float | None,
    history_result: MarketBarSymbolResult | None,
    observation_dates: tuple[date, ...],
) -> DashboardHolding:
    sparkline, history_warnings = _sparkline(
        asset=asset,
        history_result=history_result,
        observation_dates=observation_dates,
    )
    selected_period_return, return_reason = _selected_period_return(
        sparkline=sparkline,
        history_result=history_result,
    )

    warnings = [
        DashboardHoldingWarning(
            code=DashboardHoldingWarningCode.CURRENT_PRICE_WARNING,
            message=message,
            asset_id=asset.id,
            symbol=asset.symbol,
        )
        for message in current_warning_messages
    ]
    warnings.extend(history_warnings)

    market_value = None
    if current_price is not None:
        market_value = quantity * current_price.raw_close

    weight_reason = None
    if weight is None:
        weight_reason = HoldingMetricUnavailableReason.CURRENT_ALLOCATION_UNAVAILABLE

    return DashboardHolding(
        asset_id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_type=asset.asset_type,
        currency=asset.currency,
        quantity=quantity,
        current_price=(current_price.raw_close if current_price is not None else None),
        current_price_date=(current_price.trade_date if current_price is not None else None),
        current_price_retrieved_at=(current_retrieved_at if current_price is not None else None),
        stale_trading_sessions=(
            current_price.stale_trading_sessions if current_price is not None else None
        ),
        market_value=market_value,
        weight=weight,
        weight_unavailable_reason=weight_reason,
        selected_period_return=selected_period_return,
        selected_period_return_unavailable_reason=return_reason,
        contribution_to_return=None,
        contribution_unavailable_reason=(
            HoldingMetricUnavailableReason.CONTRIBUTION_NOT_CALCULATED
        ),
        sparkline=sparkline,
        data_quality=_holding_quality(
            current_price=current_price,
            sparkline=sparkline,
        ),
        warnings=tuple(warnings),
    )


def _sparkline(
    *,
    asset: Asset,
    history_result: MarketBarSymbolResult | None,
    observation_dates: tuple[date, ...],
) -> tuple[
    tuple[HoldingSparklinePoint, ...],
    tuple[DashboardHoldingWarning, ...],
]:
    if history_result is None or history_result.status is not MarketBarStatus.SUCCEEDED:
        warning = _history_status_warning(
            asset=asset,
            history_result=history_result,
        )
        return (
            tuple(
                HoldingSparklinePoint(
                    observation_date=observation_date,
                    adjusted_close=None,
                )
                for observation_date in observation_dates
            ),
            (warning,),
        )

    price_by_date = {
        bar.trade_date: Decimal(str(bar.adjusted_close))
        for bar in history_result.bars
        if bar.adjusted_close is not None
    }
    points: list[HoldingSparklinePoint] = []
    warnings = [
        DashboardHoldingWarning(
            code=DashboardHoldingWarningCode.PERIOD_PROVIDER_WARNING,
            message=message,
            asset_id=asset.id,
            symbol=asset.symbol,
        )
        for message in history_result.warnings
    ]

    for observation_date in observation_dates:
        adjusted_close = price_by_date.get(observation_date)
        points.append(
            HoldingSparklinePoint(
                observation_date=observation_date,
                adjusted_close=adjusted_close,
            )
        )

        if adjusted_close is None:
            warnings.append(
                DashboardHoldingWarning(
                    code=(DashboardHoldingWarningCode.PERIOD_MISSING_OBSERVATION),
                    message=(
                        "No adjusted-close observation exists for this "
                        "trading session; the sparkline gap was not "
                        "interpolated."
                    ),
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    observation_date=observation_date,
                )
            )

    return tuple(points), tuple(warnings)


def _history_status_warning(
    *,
    asset: Asset,
    history_result: MarketBarSymbolResult | None,
) -> DashboardHoldingWarning:
    if history_result is None or history_result.status is MarketBarStatus.NOT_FOUND:
        code = DashboardHoldingWarningCode.PERIOD_NOT_FOUND
        message = "The holding could not be resolved for selected-period history."
    elif history_result.status is MarketBarStatus.NO_DATA:
        code = DashboardHoldingWarningCode.PERIOD_NO_DATA
        message = "No selected-period price history is available for the holding."
    else:
        code = DashboardHoldingWarningCode.PERIOD_PROVIDER_FAILED
        message = "The provider failed to return selected-period holding history."

    return DashboardHoldingWarning(
        code=code,
        message=message,
        asset_id=asset.id,
        symbol=asset.symbol,
    )


def _selected_period_return(
    *,
    sparkline: tuple[HoldingSparklinePoint, ...],
    history_result: MarketBarSymbolResult | None,
) -> tuple[
    float | None,
    HoldingMetricUnavailableReason | None,
]:
    if history_result is None or history_result.status is not MarketBarStatus.SUCCEEDED:
        return (
            None,
            HoldingMetricUnavailableReason.PERIOD_HISTORY_UNAVAILABLE,
        )

    first_price = sparkline[0].adjusted_close
    last_price = sparkline[-1].adjusted_close

    if first_price is None:
        return (
            None,
            HoldingMetricUnavailableReason.PERIOD_START_PRICE_UNAVAILABLE,
        )

    if last_price is None:
        return (
            None,
            HoldingMetricUnavailableReason.PERIOD_END_PRICE_UNAVAILABLE,
        )

    return (
        simple_returns(
            (
                float(first_price),
                float(last_price),
            )
        )[0],
        None,
    )


def _holding_quality(
    *,
    current_price: CurrentPositionPrice | None,
    sparkline: tuple[HoldingSparklinePoint, ...],
) -> PerformanceDataQualityState:
    if current_price is None:
        return PerformanceDataQualityState.UNAVAILABLE

    if any(point.adjusted_close is None for point in sparkline):
        return PerformanceDataQualityState.PARTIAL

    if current_price.stale_trading_sessions > 0:
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT


def _overall_quality(
    holdings: tuple[DashboardHolding, ...],
) -> PerformanceDataQualityState:
    if not holdings:
        return PerformanceDataQualityState.CURRENT

    states = tuple(holding.data_quality for holding in holdings)

    if all(state is PerformanceDataQualityState.UNAVAILABLE for state in states):
        return PerformanceDataQualityState.UNAVAILABLE

    if any(
        state
        in (
            PerformanceDataQualityState.PARTIAL,
            PerformanceDataQualityState.UNAVAILABLE,
        )
        for state in states
    ):
        return PerformanceDataQualityState.PARTIAL

    if any(state is PerformanceDataQualityState.STALE for state in states):
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT


def _provenance(
    *,
    portfolio: Portfolio,
    current: CurrentPortfolioValuationResult,
    requested_start: date,
    requested_end: date,
    observation_dates: tuple[date, ...],
    period_data_as_of: datetime | None,
    calculated_at: datetime,
) -> DashboardHoldingsProvenance:
    return DashboardHoldingsProvenance(
        portfolio_id=portfolio.id,
        base_currency=portfolio.base_currency,
        provider=current.provenance.provider,
        requested_start=requested_start,
        requested_end_exclusive=requested_end,
        effective_start=observation_dates[0],
        effective_end_exclusive=(observation_dates[-1] + timedelta(days=1)),
        current_price_as_of=current.provenance.retrieved_at,
        period_data_as_of=period_data_as_of,
        calculated_at=calculated_at,
        current_price_field="close",
        period_price_field="adjusted_close",
    )
