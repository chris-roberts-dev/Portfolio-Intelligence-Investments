"""Display-ready P1 movers and return-contribution rankings.

Selected-period price movers use the existing dashboard holdings contract.
Return contributors use the framework-independent actual-portfolio attribution
contract and the canonical daily TWR series. Ranking and tie-breaking are
server-side and deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
    TradingSessionCalendar,
)
from apps.portfolios.services.daily_performance import (
    DailyPerformanceWarningCode,
    DailyPortfolioPerformanceResult,
    DailyPortfolioValuation,
    calculate_owned_portfolio_daily_performance,
)
from apps.portfolios.services.dashboard_holdings import (
    DashboardHolding,
    DashboardHoldingsResult,
    HoldingSparklinePoint,
    build_owned_portfolio_dashboard_holdings,
)
from apps.portfolios.services.dashboard_performance import (
    PerformanceDataQualityState,
)
from portfolio_engine.portfolio.return_attribution import (
    AssetPeriodValueChange,
    LinkedReturnAttributionResult,
    ReturnAttributionError,
    attribute_daily_portfolio_return,
    link_daily_return_attributions,
)
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION

ZERO = Decimal("0")
ATTRIBUTION_METHOD = "ASSET_PNL_WEALTH_LINKED_V1"


class DashboardMoversError(ValueError):
    """Raised when mover rankings cannot be assembled safely."""


class MoversAttributionStatus(StrEnum):
    """Availability of selected-period contribution attribution."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class MoversAttributionUnavailableReason(StrEnum):
    """Stable reason contribution attribution is unavailable."""

    PORTFOLIO_TWR_UNAVAILABLE = "PORTFOLIO_TWR_UNAVAILABLE"


class MoverUnavailableReason(StrEnum):
    """Stable null reasons for one mover row."""

    NOT_CURRENT_HOLDING = "NOT_CURRENT_HOLDING"
    SELECTED_PERIOD_RETURN_UNAVAILABLE = "SELECTED_PERIOD_RETURN_UNAVAILABLE"
    CONTRIBUTION_UNAVAILABLE = "CONTRIBUTION_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class DashboardMover:
    """One server-ranked holding or historical contributor."""

    asset_id: UUID
    symbol: str
    name: str
    asset_type: str
    currency: str
    is_current_holding: bool
    quantity: Decimal | None
    current_price: Decimal | None
    current_price_date: date | None
    current_price_retrieved_at: datetime | None
    stale_trading_sessions: int | None
    market_value: Decimal | None
    weight: float | None
    selected_period_return: float | None
    contribution_to_return: float | None
    sparkline: tuple[HoldingSparklinePoint, ...]
    data_quality: PerformanceDataQualityState
    unavailable_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MoversReconciliation:
    """Selected-period contribution reconciliation to canonical TWR."""

    status: MoversAttributionStatus
    periods: int
    cumulative_return: float | None
    asset_contribution_total: float | None
    unattributed_contribution: float | None
    reconciliation_error: float | None
    unavailable_reason: MoversAttributionUnavailableReason | None


@dataclass(frozen=True, slots=True)
class DashboardMoversProvenance:
    """Requested period and market/calculation provenance for mover rankings."""

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
    attribution_method: str
    engine_version: str


@dataclass(frozen=True, slots=True)
class DashboardMoversResult:
    """P1 gain/loss and contribution rankings for one owned portfolio."""

    top_gainers: tuple[DashboardMover, ...]
    top_losers: tuple[DashboardMover, ...]
    largest_contributors: tuple[DashboardMover, ...]
    largest_detractors: tuple[DashboardMover, ...]
    reconciliation: MoversReconciliation
    data_quality: PerformanceDataQualityState
    warnings: tuple[str, ...]
    provenance: DashboardMoversProvenance


def build_owned_portfolio_dashboard_movers(
    *,
    user: User,
    portfolio_id: UUID,
    valuation_times: tuple[datetime, ...],
    requested_start: date,
    requested_end: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    calculated_at: datetime,
    limit: int,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardMoversResult:
    """Build deterministic price-mover and contribution rankings."""
    _validate_request_context(
        valuation_times=valuation_times,
        requested_start=requested_start,
        requested_end=requested_end,
        calculated_at=calculated_at,
        limit=limit,
    )
    portfolio = Portfolio.objects.owned_by(user).get(id=portfolio_id)
    observation_dates = tuple(value.date() for value in valuation_times)
    holdings = build_owned_portfolio_dashboard_holdings(
        user=user,
        portfolio_id=portfolio_id,
        observation_dates=observation_dates,
        requested_start=requested_start,
        requested_end=requested_end,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        calculated_at=calculated_at,
        executor=executor,
    )
    performance = calculate_owned_portfolio_daily_performance(
        user=user,
        portfolio_id=portfolio_id,
        valuation_times=valuation_times,
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
    )

    if holdings.provenance.provider != performance.provenance.provider:
        raise DashboardMoversError("Holdings and performance mover inputs must use one provider.")

    linked, unavailable_reason = _linked_attribution(
        portfolio=portfolio,
        valuation_times=valuation_times,
        performance=performance,
    )
    movers = _mover_universe(
        holdings=holdings,
        performance=performance,
        linked=linked,
        unavailable_reason=unavailable_reason,
    )
    reconciliation = _reconciliation(
        linked=linked,
        unavailable_reason=unavailable_reason,
    )

    return DashboardMoversResult(
        top_gainers=_rank_positive(
            movers,
            metric="selected_period_return",
            limit=limit,
        ),
        top_losers=_rank_negative(
            movers,
            metric="selected_period_return",
            limit=limit,
        ),
        largest_contributors=_rank_positive(
            movers,
            metric="contribution_to_return",
            limit=limit,
        ),
        largest_detractors=_rank_negative(
            movers,
            metric="contribution_to_return",
            limit=limit,
        ),
        reconciliation=reconciliation,
        data_quality=_overall_quality(
            holdings=holdings,
            attribution_available=linked is not None,
        ),
        warnings=_warnings(
            holdings=holdings,
            performance=performance,
            unavailable_reason=unavailable_reason,
        ),
        provenance=DashboardMoversProvenance(
            portfolio_id=portfolio.id,
            base_currency=portfolio.base_currency,
            provider=performance.provenance.provider,
            requested_start=requested_start,
            requested_end_exclusive=requested_end,
            effective_start=valuation_times[0].date(),
            effective_end_exclusive=(valuation_times[-1].date() + timedelta(days=1)),
            current_price_as_of=holdings.provenance.current_price_as_of,
            period_data_as_of=_latest_timestamp(
                holdings.provenance.period_data_as_of,
                performance.provenance.retrieved_at,
            ),
            calculated_at=calculated_at,
            current_price_field="close",
            period_price_field="adjusted_close",
            attribution_method=ATTRIBUTION_METHOD,
            engine_version=PORTFOLIO_ENGINE_VERSION,
        ),
    )


def _validate_request_context(
    *,
    valuation_times: tuple[datetime, ...],
    requested_start: date,
    requested_end: date,
    calculated_at: datetime,
    limit: int,
) -> None:
    if requested_start >= requested_end:
        raise DashboardMoversError("requested_start must be before requested_end")

    if len(valuation_times) < 2:
        raise DashboardMoversError("dashboard movers require at least two valuation times")

    if tuple(sorted(set(valuation_times))) != valuation_times:
        raise DashboardMoversError("valuation_times must be unique and strictly ascending")

    if any(timezone.is_naive(value) for value in valuation_times):
        raise DashboardMoversError("valuation_times must be timezone-aware")

    if valuation_times[0].date() < requested_start or valuation_times[-1].date() >= requested_end:
        raise DashboardMoversError("valuation times must remain inside the requested range")

    if timezone.is_naive(calculated_at):
        raise DashboardMoversError("calculated_at must be timezone-aware")

    if not 1 <= limit <= 20:
        raise DashboardMoversError("limit must be between 1 and 20")


def _linked_attribution(
    *,
    portfolio: Portfolio,
    valuation_times: tuple[datetime, ...],
    performance: DailyPortfolioPerformanceResult,
) -> tuple[
    LinkedReturnAttributionResult | None,
    MoversAttributionUnavailableReason | None,
]:
    if performance.twr is None:
        return (
            None,
            MoversAttributionUnavailableReason.PORTFOLIO_TWR_UNAVAILABLE,
        )

    if len(performance.valuations) != len(valuation_times):
        raise DashboardMoversError(
            "Performance valuation count does not match requested boundaries."
        )

    if len(performance.twr.daily_returns) != len(valuation_times) - 1:
        raise DashboardMoversError("Daily TWR count does not match valuation periods.")

    internal_flows = _internal_asset_cash_flows_by_period(
        portfolio=portfolio,
        valuation_times=valuation_times,
    )
    daily_results = []

    try:
        for prior, ending, daily_return, period_flows in zip(
            performance.valuations[:-1],
            performance.valuations[1:],
            performance.twr.daily_returns,
            internal_flows,
            strict=True,
        ):
            if daily_return.valuation_date != ending.as_of.date():
                raise DashboardMoversError("Daily TWR endpoint does not match valuation endpoint.")

            daily_results.append(
                attribute_daily_portfolio_return(
                    period_start=prior.as_of.date(),
                    period_end=ending.as_of.date(),
                    prior_portfolio_value=daily_return.prior_portfolio_value,
                    portfolio_return=daily_return.simple_return,
                    assets=_asset_period_changes(
                        prior=prior,
                        ending=ending,
                        internal_flows=period_flows,
                    ),
                )
            )

        linked = link_daily_return_attributions(tuple(daily_results))
    except ReturnAttributionError as exc:
        raise DashboardMoversError(str(exc)) from exc

    tolerance = max(
        1e-12,
        math.ulp(linked.cumulative_return),
        math.ulp(performance.twr.cumulative_return),
    )
    if abs(linked.cumulative_return - performance.twr.cumulative_return) > tolerance:
        raise DashboardMoversError("Linked asset attribution does not reconcile to portfolio TWR.")

    return linked, None


def _internal_asset_cash_flows_by_period(
    *,
    portfolio: Portfolio,
    valuation_times: tuple[datetime, ...],
) -> tuple[dict[UUID, Decimal], ...]:
    period_flows: list[dict[UUID, Decimal]] = [{} for _ in range(len(valuation_times) - 1)]
    transactions = tuple(
        Transaction.objects.for_portfolio(portfolio)
        .filter(
            transaction_type__in=(
                TransactionType.BUY,
                TransactionType.SELL,
                TransactionType.DIVIDEND,
            ),
            occurred_at__gt=valuation_times[0],
            occurred_at__lte=valuation_times[-1],
        )
        .ordered_for_replay()
    )
    period_index = 0

    for transaction in transactions:
        while (
            period_index < len(period_flows)
            and transaction.occurred_at > valuation_times[period_index + 1]
        ):
            period_index += 1

        if period_index >= len(period_flows):
            break

        if transaction.occurred_at <= valuation_times[period_index]:
            continue

        asset_id = transaction.asset_id
        if asset_id is None:
            raise DashboardMoversError(f"Internal transaction {transaction.id} requires an asset.")

        amount = _signed_internal_asset_cash_flow(transaction)
        period_flows[period_index][asset_id] = (
            period_flows[period_index].get(asset_id, ZERO) + amount
        )

    return tuple(period_flows)


def _signed_internal_asset_cash_flow(
    transaction: Transaction,
) -> Decimal:
    transaction_type = TransactionType(transaction.transaction_type)

    if transaction_type is TransactionType.BUY:
        quantity = _required_decimal(
            transaction.quantity,
            field_name="quantity",
            transaction=transaction,
        )
        price = _required_decimal(
            transaction.price,
            field_name="price",
            transaction=transaction,
        )
        return -(quantity * price + transaction.fees)

    if transaction_type is TransactionType.SELL:
        quantity = _required_decimal(
            transaction.quantity,
            field_name="quantity",
            transaction=transaction,
        )
        price = _required_decimal(
            transaction.price,
            field_name="price",
            transaction=transaction,
        )
        return quantity * price - transaction.fees

    if transaction_type is TransactionType.DIVIDEND:
        return _required_decimal(
            transaction.cash_amount,
            field_name="cash_amount",
            transaction=transaction,
        )

    raise DashboardMoversError(f"Transaction {transaction.id} is not an internal asset cash flow.")


def _required_decimal(
    value: Decimal | None,
    *,
    field_name: str,
    transaction: Transaction,
) -> Decimal:
    if value is None:
        raise DashboardMoversError(f"Transaction {transaction.id} requires {field_name}.")

    return value


def _asset_period_changes(
    *,
    prior: DailyPortfolioValuation,
    ending: DailyPortfolioValuation,
    internal_flows: dict[UUID, Decimal],
) -> tuple[AssetPeriodValueChange, ...]:
    starting_values = {position.asset_id: position.market_value for position in prior.positions}
    ending_values = {position.asset_id: position.market_value for position in ending.positions}
    asset_ids = set(starting_values) | set(ending_values) | set(internal_flows)

    return tuple(
        AssetPeriodValueChange(
            asset_id=asset_id,
            starting_market_value=_decimal_to_float(
                starting_values.get(asset_id, ZERO),
                field_name="starting_market_value",
            ),
            ending_market_value=_decimal_to_float(
                ending_values.get(asset_id, ZERO),
                field_name="ending_market_value",
            ),
            internal_cash_flow=_decimal_to_float(
                internal_flows.get(asset_id, ZERO),
                field_name="internal_cash_flow",
            ),
        )
        for asset_id in sorted(asset_ids, key=lambda value: value.hex)
    )


def _mover_universe(
    *,
    holdings: DashboardHoldingsResult,
    performance: DailyPortfolioPerformanceResult,
    linked: LinkedReturnAttributionResult | None,
    unavailable_reason: MoversAttributionUnavailableReason | None,
) -> tuple[DashboardMover, ...]:
    holding_by_asset = {holding.asset_id: holding for holding in holdings.holdings}
    contribution_by_asset = (
        {item.asset_id: item.contribution for item in linked.asset_contributions}
        if linked is not None
        else {}
    )
    asset_ids = set(holding_by_asset) | set(contribution_by_asset)
    assets = Asset.objects.in_bulk(asset_ids)
    missing = tuple(
        asset_id
        for asset_id in sorted(asset_ids, key=lambda value: value.hex)
        if asset_id not in assets
    )

    if missing:
        raise DashboardMoversError(f"Mover attribution references unknown asset IDs: {missing!r}.")

    return tuple(
        _build_mover(
            asset=assets[asset_id],
            holding=holding_by_asset.get(asset_id),
            contribution=(contribution_by_asset.get(asset_id, 0.0) if linked is not None else None),
            attribution_unavailable_reason=unavailable_reason,
            performance=performance,
        )
        for asset_id in sorted(asset_ids, key=lambda value: value.hex)
    )


def _build_mover(
    *,
    asset: Asset,
    holding: DashboardHolding | None,
    contribution: float | None,
    attribution_unavailable_reason: (MoversAttributionUnavailableReason | None),
    performance: DailyPortfolioPerformanceResult,
) -> DashboardMover:
    unavailable_reasons: list[str] = []

    if holding is None:
        unavailable_reasons.extend(
            (
                MoverUnavailableReason.NOT_CURRENT_HOLDING.value,
                MoverUnavailableReason.SELECTED_PERIOD_RETURN_UNAVAILABLE.value,
            )
        )
    elif holding.selected_period_return is None:
        if holding.selected_period_return_unavailable_reason is not None:
            unavailable_reasons.append(holding.selected_period_return_unavailable_reason.value)
        else:
            unavailable_reasons.append(
                MoverUnavailableReason.SELECTED_PERIOD_RETURN_UNAVAILABLE.value
            )

    if attribution_unavailable_reason is not None:
        unavailable_reasons.append(MoverUnavailableReason.CONTRIBUTION_UNAVAILABLE.value)
        unavailable_reasons.append(attribution_unavailable_reason.value)

    return DashboardMover(
        asset_id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_type=asset.asset_type,
        currency=asset.currency,
        is_current_holding=holding is not None,
        quantity=holding.quantity if holding is not None else None,
        current_price=(holding.current_price if holding is not None else None),
        current_price_date=(holding.current_price_date if holding is not None else None),
        current_price_retrieved_at=(
            holding.current_price_retrieved_at if holding is not None else None
        ),
        stale_trading_sessions=(holding.stale_trading_sessions if holding is not None else None),
        market_value=(holding.market_value if holding is not None else None),
        weight=holding.weight if holding is not None else None,
        selected_period_return=(holding.selected_period_return if holding is not None else None),
        contribution_to_return=contribution,
        sparkline=holding.sparkline if holding is not None else (),
        data_quality=(
            holding.data_quality
            if holding is not None
            else _historical_asset_quality(
                performance=performance,
                asset_id=asset.id,
            )
        ),
        unavailable_reasons=tuple(unavailable_reasons),
    )


def _historical_asset_quality(
    *,
    performance: DailyPortfolioPerformanceResult,
    asset_id: UUID,
) -> PerformanceDataQualityState:
    asset_warnings = tuple(
        warning for warning in performance.warnings if warning.asset_id == asset_id
    )

    if any(
        warning.code
        in (
            DailyPerformanceWarningCode.PRICE_NOT_FOUND,
            DailyPerformanceWarningCode.PRICE_NO_DATA,
            DailyPerformanceWarningCode.PRICE_PROVIDER_FAILED,
            DailyPerformanceWarningCode.PRICE_TOO_STALE,
            DailyPerformanceWarningCode.PRICE_DATE_OUTSIDE_SESSION_CALENDAR,
        )
        for warning in asset_warnings
    ):
        return PerformanceDataQualityState.PARTIAL

    if any(
        warning.code is DailyPerformanceWarningCode.STALE_PRICE_USED for warning in asset_warnings
    ):
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT


def _rank_positive(
    movers: tuple[DashboardMover, ...],
    *,
    metric: str,
    limit: int,
) -> tuple[DashboardMover, ...]:
    eligible = tuple(
        mover
        for mover in movers
        if ((value := _metric_value(mover, metric)) is not None and value > 0.0)
    )
    return tuple(
        sorted(
            eligible,
            key=lambda mover: (
                -_required_metric_value(mover, metric),
                mover.symbol.casefold(),
                mover.asset_id.hex,
            ),
        )[:limit]
    )


def _rank_negative(
    movers: tuple[DashboardMover, ...],
    *,
    metric: str,
    limit: int,
) -> tuple[DashboardMover, ...]:
    eligible = tuple(
        mover
        for mover in movers
        if ((value := _metric_value(mover, metric)) is not None and value < 0.0)
    )
    return tuple(
        sorted(
            eligible,
            key=lambda mover: (
                _required_metric_value(mover, metric),
                mover.symbol.casefold(),
                mover.asset_id.hex,
            ),
        )[:limit]
    )


def _metric_value(
    mover: DashboardMover,
    metric: str,
) -> float | None:
    if metric == "selected_period_return":
        return mover.selected_period_return

    if metric == "contribution_to_return":
        return mover.contribution_to_return

    raise DashboardMoversError(f"Unsupported mover metric {metric!r}.")


def _required_metric_value(
    mover: DashboardMover,
    metric: str,
) -> float:
    value = _metric_value(mover, metric)

    if value is None:
        raise DashboardMoversError(f"Mover {mover.asset_id} has no value for {metric}.")

    return value


def _reconciliation(
    *,
    linked: LinkedReturnAttributionResult | None,
    unavailable_reason: MoversAttributionUnavailableReason | None,
) -> MoversReconciliation:
    if linked is None:
        return MoversReconciliation(
            status=MoversAttributionStatus.UNAVAILABLE,
            periods=0,
            cumulative_return=None,
            asset_contribution_total=None,
            unattributed_contribution=None,
            reconciliation_error=None,
            unavailable_reason=unavailable_reason,
        )

    return MoversReconciliation(
        status=MoversAttributionStatus.AVAILABLE,
        periods=linked.periods,
        cumulative_return=linked.cumulative_return,
        asset_contribution_total=linked.asset_contribution_total,
        unattributed_contribution=linked.unattributed_contribution,
        reconciliation_error=linked.reconciliation_error,
        unavailable_reason=None,
    )


def _overall_quality(
    *,
    holdings: DashboardHoldingsResult,
    attribution_available: bool,
) -> PerformanceDataQualityState:
    if not attribution_available:
        return PerformanceDataQualityState.PARTIAL

    return holdings.data_quality


def _warnings(
    *,
    holdings: DashboardHoldingsResult,
    performance: DailyPortfolioPerformanceResult,
    unavailable_reason: MoversAttributionUnavailableReason | None,
) -> tuple[str, ...]:
    messages = [warning.message for warning in holdings.warnings]
    messages.extend(warning.message for warning in performance.warnings)

    if unavailable_reason is not None:
        messages.append(
            "Contribution rankings are unavailable because canonical "
            "portfolio TWR is undefined for the selected period."
        )

    return tuple(dict.fromkeys(messages))


def _latest_timestamp(
    first: datetime | None,
    second: datetime | None,
) -> datetime | None:
    if first is None:
        return second

    if second is None:
        return first

    return max(first, second)


def _decimal_to_float(
    value: Decimal,
    *,
    field_name: str,
) -> float:
    converted = float(value)

    if not math.isfinite(converted):
        raise DashboardMoversError(f"{field_name} cannot be represented as a finite value.")

    return converted
