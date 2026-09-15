"""Daily owned-portfolio valuation series and canonical daily TWR.

Development guide references: Sections 9.6, 9.7, and 10.1-10.4.

Historical performance uses adjusted close. Holdings and cash are replayed from
the authoritative transaction ledger at each valuation endpoint. Deposits and
withdrawals are the only external flows; BUY, SELL, and DIVIDEND remain internal
portfolio activity.

The MVP deliberately uses the guide's daily cash-flow convention. It does not
attempt intraday or transaction-boundary TWR.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.market_data.contracts import (
    MarketBarBatchResult,
    MarketBarStatus,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio, Transaction, TransactionType
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
    TradingSessionCalendar,
)
from apps.portfolios.services.ledger import (
    LedgerReplayResult,
    replay_portfolio_ledger,
)
from portfolio_engine.config import (
    MAX_BAR_QUERY_SYMBOLS,
    MAX_STALE_PRICE_TRADING_SESSIONS,
)
from portfolio_engine.performance.time_weighted import (
    DailyPortfolioValue,
    TimeWeightedReturnError,
    TimeWeightedReturnResult,
    calculate_daily_time_weighted_return,
)

ZERO = Decimal("0")


class DailyPerformanceError(ValueError):
    """Raised when a daily performance request is structurally invalid."""


class DailyPerformanceWarningCode(StrEnum):
    """Stable warnings for historical portfolio valuation and TWR."""

    STALE_PRICE_USED = "STALE_PRICE_USED"
    PRICE_NOT_FOUND = "PRICE_NOT_FOUND"
    PRICE_NO_DATA = "PRICE_NO_DATA"
    PRICE_PROVIDER_FAILED = "PRICE_PROVIDER_FAILED"
    PRICE_TOO_STALE = "PRICE_TOO_STALE"
    PRICE_DATE_OUTSIDE_SESSION_CALENDAR = "PRICE_DATE_OUTSIDE_SESSION_CALENDAR"
    INCOMPLETE_VALUATION = "INCOMPLETE_VALUATION"
    TWR_UNDEFINED = "TWR_UNDEFINED"


@dataclass(frozen=True, slots=True)
class DailyPerformanceWarning:
    """One warning attached to a historical performance result."""

    code: DailyPerformanceWarningCode
    message: str
    valuation_at: datetime
    asset_id: UUID | None = None
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class DailyAssetValuation:
    """One held asset valued with adjusted close."""

    asset_id: UUID
    symbol: str
    quantity: Decimal
    price_date: date
    adjusted_close: Decimal
    market_value: Decimal
    stale_trading_sessions: int


@dataclass(frozen=True, slots=True)
class DailyPortfolioValuation:
    """One end-of-day ledger-derived portfolio valuation."""

    as_of: datetime
    cash_balance: Decimal
    security_value: Decimal | None
    total_value: Decimal | None
    net_external_flow: Decimal
    positions: tuple[DailyAssetValuation, ...]
    warnings: tuple[DailyPerformanceWarning, ...]
    is_complete: bool


@dataclass(frozen=True, slots=True)
class DailyPerformanceProvenance:
    """Historical performance data and price provenance."""

    portfolio_id: UUID
    benchmark_asset_id: UUID | None
    provider: str
    retrieved_at: datetime | None
    price_field: str
    period_start: date
    period_end: date


@dataclass(frozen=True, slots=True)
class DailyPortfolioPerformanceResult:
    """Daily valuations plus canonical chain-linked TWR."""

    valuations: tuple[DailyPortfolioValuation, ...]
    twr: TimeWeightedReturnResult | None
    warnings: tuple[DailyPerformanceWarning, ...]
    provenance: DailyPerformanceProvenance


def calculate_owned_portfolio_daily_performance(
    *,
    user: User,
    portfolio_id: UUID,
    valuation_times: Sequence[datetime],
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DailyPortfolioPerformanceResult:
    """Build a daily adjusted-close valuation series and canonical daily TWR."""
    times = _validated_valuation_times(valuation_times)
    portfolio = (
        Portfolio.objects.owned_by(user).select_related("benchmark_asset").get(id=portfolio_id)
    )
    ledgers = tuple(
        replay_portfolio_ledger(
            portfolio,
            as_of=as_of,
        )
        for as_of in times
    )
    external_flows = _external_flows_by_valuation(
        portfolio=portfolio,
        valuation_times=times,
    )
    assets = _assets_for_ledgers(ledgers)
    _reject_duplicate_symbols(assets)

    result_by_symbol: dict[str, Any] = {}
    retrieved_at: datetime | None = None
    resolved_provider = provider_name

    if assets:
        query_start = _query_start(
            trading_calendar=trading_calendar,
            first_valuation=times[0],
        )
        (
            result_by_symbol,
            resolved_provider,
            retrieved_at,
        ) = _load_market_results(
            assets=assets,
            start=query_start,
            end=times[-1].date() + timedelta(days=1),
            provider_name=provider_name,
            resolver=resolver,
            provider=provider,
            executor=executor,
        )

    valuations = tuple(
        _value_daily_portfolio(
            as_of=as_of,
            ledger=ledger,
            net_external_flow=external_flow,
            assets=assets,
            result_by_symbol=result_by_symbol,
            trading_calendar=trading_calendar,
        )
        for as_of, ledger, external_flow in zip(
            times,
            ledgers,
            external_flows,
            strict=True,
        )
    )

    warnings = tuple(warning for valuation in valuations for warning in valuation.warnings)
    twr, twr_warning = _calculate_twr(valuations)

    if twr_warning is not None:
        warnings = (*warnings, twr_warning)

    return DailyPortfolioPerformanceResult(
        valuations=valuations,
        twr=twr,
        warnings=warnings,
        provenance=DailyPerformanceProvenance(
            portfolio_id=portfolio.id,
            benchmark_asset_id=portfolio.benchmark_asset_id,
            provider=resolved_provider,
            retrieved_at=retrieved_at,
            price_field="adjusted_close",
            period_start=times[0].date(),
            period_end=times[-1].date(),
        ),
    )


def _validated_valuation_times(
    valuation_times: Sequence[datetime],
) -> tuple[datetime, ...]:
    times = tuple(valuation_times)

    if len(times) < 2:
        raise DailyPerformanceError(
            "daily portfolio performance requires at least two valuation times"
        )

    previous: datetime | None = None
    seen_dates: set[date] = set()

    for value in times:
        if timezone.is_naive(value):
            raise DailyPerformanceError("valuation times must be timezone-aware")

        if previous is not None and value <= previous:
            raise DailyPerformanceError("valuation times must be strictly ascending")

        if value.date() in seen_dates:
            raise DailyPerformanceError("daily performance permits one valuation per calendar date")

        seen_dates.add(value.date())
        previous = value

    return times


def _external_flows_by_valuation(
    *,
    portfolio: Portfolio,
    valuation_times: tuple[datetime, ...],
) -> tuple[Decimal, ...]:
    transactions = tuple(
        Transaction.objects.for_portfolio(portfolio)
        .filter(
            transaction_type__in=(
                TransactionType.DEPOSIT,
                TransactionType.WITHDRAWAL,
            ),
            occurred_at__gt=valuation_times[0],
            occurred_at__lte=valuation_times[-1],
        )
        .ordered_for_replay()
    )

    flows: list[Decimal] = [ZERO]
    transaction_index = 0

    for prior_time, current_time in zip(
        valuation_times,
        valuation_times[1:],
        strict=False,
    ):
        net_flow = ZERO

        while transaction_index < len(transactions):
            transaction = transactions[transaction_index]

            if transaction.occurred_at > current_time:
                break

            if transaction.occurred_at > prior_time:
                net_flow += _signed_external_flow(transaction)

            transaction_index += 1

        flows.append(net_flow)

    return tuple(flows)


def _signed_external_flow(
    transaction: Transaction,
) -> Decimal:
    if transaction.cash_amount is None:
        raise DailyPerformanceError(
            f"External-flow transaction {transaction.id} has no cash amount."
        )

    if transaction.transaction_type == TransactionType.DEPOSIT:
        return transaction.cash_amount

    if transaction.transaction_type == TransactionType.WITHDRAWAL:
        return -transaction.cash_amount

    raise DailyPerformanceError(f"Transaction {transaction.id} is not an external cash flow.")


def _assets_for_ledgers(
    ledgers: tuple[LedgerReplayResult, ...],
) -> dict[UUID, Asset]:
    asset_ids = {position.asset_id for ledger in ledgers for position in ledger.positions}
    assets = Asset.objects.in_bulk(asset_ids)

    missing = tuple(
        sorted(
            (asset_id for asset_id in asset_ids if asset_id not in assets),
            key=lambda value: value.hex,
        )
    )

    if missing:
        raise DailyPerformanceError(f"Ledger references unknown asset IDs: {missing!r}.")

    return assets


def _reject_duplicate_symbols(
    assets: dict[UUID, Asset],
) -> None:
    symbols = tuple(asset.symbol for asset in assets.values())

    if len(symbols) != len(set(symbols)):
        raise DailyPerformanceError("Historical valuation requires unique canonical symbols.")


def _query_start(
    *,
    trading_calendar: TradingSessionCalendar,
    first_valuation: datetime,
) -> date:
    sessions = _session_window(
        trading_calendar,
        valuation_date=first_valuation.date(),
    )
    return sessions[0]


def _load_market_results(
    *,
    assets: dict[UUID, Asset],
    start: date,
    end: date,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> tuple[dict[str, Any], str, datetime | None]:
    symbols = tuple(sorted(asset.symbol for asset in assets.values()))
    results: dict[str, Any] = {}
    resolved_provider: str | None = None
    retrieved_at: datetime | None = None

    for offset in range(
        0,
        len(symbols),
        MAX_BAR_QUERY_SYMBOLS,
    ):
        symbol_batch = symbols[offset : offset + MAX_BAR_QUERY_SYMBOLS]
        query = normalize_market_bar_query(
            symbol_batch,
            start=start,
            end=end,
            provider=provider_name,
        )
        batch = executor(
            query,
            resolver=resolver,
            provider=provider,
        )
        resolved_provider = _merge_provider(
            resolved_provider,
            batch,
        )
        retrieved_at = _latest_retrieval(
            retrieved_at,
            batch,
        )

        for symbol_result in batch.results:
            if symbol_result.symbol in results:
                raise DailyPerformanceError(
                    f"Duplicate market-data result for {symbol_result.symbol}."
                )

            results[symbol_result.symbol] = symbol_result

    return (
        results,
        resolved_provider or provider_name,
        retrieved_at,
    )


def _merge_provider(
    current: str | None,
    batch: MarketBarBatchResult,
) -> str:
    if current is None:
        return batch.meta.provider

    if batch.meta.provider != current:
        raise DailyPerformanceError("Historical valuation batches returned inconsistent providers.")

    return current


def _latest_retrieval(
    current: datetime | None,
    batch: MarketBarBatchResult,
) -> datetime:
    retrieved_at = batch.meta.retrieved_at

    if current is None:
        return retrieved_at

    return max(current, retrieved_at)


def _value_daily_portfolio(
    *,
    as_of: datetime,
    ledger: LedgerReplayResult,
    net_external_flow: Decimal,
    assets: dict[UUID, Asset],
    result_by_symbol: dict[str, Any],
    trading_calendar: TradingSessionCalendar,
) -> DailyPortfolioValuation:
    sessions = _session_window(
        trading_calendar,
        valuation_date=as_of.date(),
    )
    position_values: list[DailyAssetValuation] = []
    warnings: list[DailyPerformanceWarning] = []

    for position in ledger.positions:
        asset = assets[position.asset_id]
        symbol_result = result_by_symbol.get(asset.symbol)

        if symbol_result is None:
            warnings.append(
                _warning(
                    code=DailyPerformanceWarningCode.PRICE_NOT_FOUND,
                    as_of=as_of,
                    asset=asset,
                    message=("No market-data result was returned for the held asset."),
                )
            )
            continue

        if symbol_result.status != MarketBarStatus.SUCCEEDED:
            warnings.append(
                _status_warning(
                    as_of=as_of,
                    asset=asset,
                    status=symbol_result.status,
                )
            )
            continue

        bars = tuple(bar for bar in symbol_result.bars if bar.trade_date <= as_of.date())

        if not bars:
            warnings.append(
                _warning(
                    code=DailyPerformanceWarningCode.PRICE_NO_DATA,
                    as_of=as_of,
                    asset=asset,
                    message=(
                        "Provider returned no adjusted-close observation "
                        "through the valuation date."
                    ),
                )
            )
            continue

        latest_bar = bars[-1]

        if latest_bar.adjusted_close is None:
            warnings.append(
                _warning(
                    code=DailyPerformanceWarningCode.PRICE_NO_DATA,
                    as_of=as_of,
                    asset=asset,
                    message=("Latest market bar has no adjusted-close value."),
                )
            )
            continue

        if latest_bar.trade_date < sessions[0]:
            warnings.append(
                _warning(
                    code=DailyPerformanceWarningCode.PRICE_TOO_STALE,
                    as_of=as_of,
                    asset=asset,
                    message=(
                        "Latest adjusted-close price exceeds the configured "
                        f"{MAX_STALE_PRICE_TRADING_SESSIONS}-session "
                        "staleness limit."
                    ),
                )
            )
            continue

        try:
            session_index = sessions.index(latest_bar.trade_date)
        except ValueError:
            warnings.append(
                _warning(
                    code=(DailyPerformanceWarningCode.PRICE_DATE_OUTSIDE_SESSION_CALENDAR),
                    as_of=as_of,
                    asset=asset,
                    message=(
                        "Latest adjusted-close date is not present in the "
                        "supplied trading-session calendar."
                    ),
                )
            )
            continue

        stale_sessions = len(sessions) - 1 - session_index

        if stale_sessions > MAX_STALE_PRICE_TRADING_SESSIONS:
            warnings.append(
                _warning(
                    code=DailyPerformanceWarningCode.PRICE_TOO_STALE,
                    as_of=as_of,
                    asset=asset,
                    message=(
                        "Latest adjusted-close price exceeds the configured "
                        f"{MAX_STALE_PRICE_TRADING_SESSIONS}-session "
                        "staleness limit."
                    ),
                )
            )
            continue

        if stale_sessions > 0:
            warnings.append(
                _warning(
                    code=DailyPerformanceWarningCode.STALE_PRICE_USED,
                    as_of=as_of,
                    asset=asset,
                    message=(
                        "Historical valuation uses an adjusted-close price "
                        f"{stale_sessions} trading session(s) stale."
                    ),
                )
            )

        price = Decimal(str(latest_bar.adjusted_close))

        position_values.append(
            DailyAssetValuation(
                asset_id=asset.id,
                symbol=asset.symbol,
                quantity=position.quantity,
                price_date=latest_bar.trade_date,
                adjusted_close=price,
                market_value=position.quantity * price,
                stale_trading_sessions=stale_sessions,
            )
        )

    is_complete = len(position_values) == len(ledger.positions)

    if is_complete:
        security_value = sum(
            (position.market_value for position in position_values),
            ZERO,
        )
        total_value = ledger.cash_balance + security_value
    else:
        security_value = None
        total_value = None
        warnings.append(
            DailyPerformanceWarning(
                code=DailyPerformanceWarningCode.INCOMPLETE_VALUATION,
                message=(
                    "Portfolio valuation is incomplete because at least one "
                    "held asset lacks an acceptable adjusted-close price."
                ),
                valuation_at=as_of,
            )
        )

    return DailyPortfolioValuation(
        as_of=as_of,
        cash_balance=ledger.cash_balance,
        security_value=security_value,
        total_value=total_value,
        net_external_flow=net_external_flow,
        positions=tuple(position_values),
        warnings=tuple(warnings),
        is_complete=is_complete,
    )


def _session_window(
    trading_calendar: TradingSessionCalendar,
    *,
    valuation_date: date,
) -> tuple[date, ...]:
    required_count = MAX_STALE_PRICE_TRADING_SESSIONS + 2
    sessions = trading_calendar.sessions_through(
        valuation_date,
        count=required_count,
    )

    if len(sessions) != required_count:
        raise DailyPerformanceError(
            f"Trading calendar must provide exactly {required_count} sessions."
        )

    if tuple(sorted(set(sessions))) != sessions:
        raise DailyPerformanceError("Trading sessions must be unique and strictly ascending.")

    if sessions[-1] > valuation_date:
        raise DailyPerformanceError("Trading sessions must not extend beyond the valuation date.")

    return sessions


def _status_warning(
    *,
    as_of: datetime,
    asset: Asset,
    status: MarketBarStatus,
) -> DailyPerformanceWarning:
    if status == MarketBarStatus.NOT_FOUND:
        code = DailyPerformanceWarningCode.PRICE_NOT_FOUND
        message = "Held asset could not be resolved for historical valuation."
    elif status == MarketBarStatus.NO_DATA:
        code = DailyPerformanceWarningCode.PRICE_NO_DATA
        message = "Provider returned no historical data for the held asset."
    else:
        code = DailyPerformanceWarningCode.PRICE_PROVIDER_FAILED
        message = "Provider failed to return usable historical data."

    return _warning(
        code=code,
        as_of=as_of,
        asset=asset,
        message=message,
    )


def _warning(
    *,
    code: DailyPerformanceWarningCode,
    as_of: datetime,
    asset: Asset,
    message: str,
) -> DailyPerformanceWarning:
    return DailyPerformanceWarning(
        code=code,
        message=message,
        valuation_at=as_of,
        asset_id=asset.id,
        symbol=asset.symbol,
    )


def _calculate_twr(
    valuations: tuple[DailyPortfolioValuation, ...],
) -> tuple[
    TimeWeightedReturnResult | None,
    DailyPerformanceWarning | None,
]:
    if any(not valuation.is_complete for valuation in valuations):
        return (
            None,
            DailyPerformanceWarning(
                code=DailyPerformanceWarningCode.TWR_UNDEFINED,
                message=("TWR is unavailable because the daily valuation series is incomplete."),
                valuation_at=valuations[-1].as_of,
            ),
        )

    engine_values = tuple(
        DailyPortfolioValue(
            valuation_date=valuation.as_of.date(),
            portfolio_value=_decimal_to_engine_float(
                _required_total_value(valuation),
                field_name="total_value",
            ),
            net_external_flow=_decimal_to_engine_float(
                valuation.net_external_flow,
                field_name="net_external_flow",
            ),
        )
        for valuation in valuations
    )

    try:
        return (
            calculate_daily_time_weighted_return(engine_values),
            None,
        )
    except TimeWeightedReturnError as exc:
        return (
            None,
            DailyPerformanceWarning(
                code=DailyPerformanceWarningCode.TWR_UNDEFINED,
                message=str(exc),
                valuation_at=valuations[-1].as_of,
            ),
        )


def _required_total_value(
    valuation: DailyPortfolioValuation,
) -> Decimal:
    if valuation.total_value is None:
        raise DailyPerformanceError("complete valuation unexpectedly has no total value")

    return valuation.total_value


def _decimal_to_engine_float(
    value: Decimal,
    *,
    field_name: str,
) -> float:
    converted = float(value)

    if not math.isfinite(converted):
        raise DailyPerformanceError(f"{field_name} cannot be represented as a finite engine value.")

    return converted
