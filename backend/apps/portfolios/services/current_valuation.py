"""Owned-portfolio current valuation and allocation application service.

Ledger replay remains the source of truth for owned quantities and cash.
Security prices are resolved through the existing provider-neutral market-bar
application boundary. Raw close is the valuation field.

Decimal values are retained through the ledger and application-price boundary.
Conversion to float occurs only when invoking the framework-independent
analytical valuation helpers.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.market_data.contracts import (
    MarketBarBatchResult,
    MarketBarStatus,
    NormalizedMarketBarQuery,
    normalize_market_bar_query,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
from apps.portfolios.services.ledger import (
    LedgerReplayResult,
    replay_portfolio_ledger,
)
from portfolio_engine.config import MAX_STALE_PRICE_TRADING_SESSIONS
from portfolio_engine.portfolio.allocation import (
    PortfolioAllocationResult,
    derive_portfolio_allocation,
)
from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    PortfolioValuationResult,
    value_portfolio,
)


class CurrentValuationError(ValueError):
    """Raised when current valuation cannot satisfy its application contract."""


class CurrentValuationWarningCode(StrEnum):
    """Stable warnings emitted by current portfolio valuation."""

    STALE_PRICE_USED = "STALE_PRICE_USED"
    PRICE_NOT_FOUND = "PRICE_NOT_FOUND"
    PRICE_NO_DATA = "PRICE_NO_DATA"
    PRICE_PROVIDER_FAILED = "PRICE_PROVIDER_FAILED"
    PRICE_TOO_STALE = "PRICE_TOO_STALE"
    PRICE_DATE_OUTSIDE_SESSION_CALENDAR = "PRICE_DATE_OUTSIDE_SESSION_CALENDAR"


@dataclass(frozen=True, slots=True)
class CurrentValuationWarning:
    """One explicit portfolio-valuation warning."""

    code: CurrentValuationWarningCode
    message: str
    asset_id: UUID
    symbol: str


@dataclass(frozen=True, slots=True)
class CurrentPositionPrice:
    """Accepted raw-close price used to value one held asset."""

    asset_id: UUID
    symbol: str
    quantity: Decimal
    trade_date: date
    raw_close: Decimal
    stale_trading_sessions: int


@dataclass(frozen=True, slots=True)
class CurrentValuationProvenance:
    """Provider and portfolio provenance for one valuation attempt."""

    portfolio_id: UUID
    benchmark_asset_id: UUID | None
    provider: str
    as_of: datetime
    retrieved_at: datetime | None
    price_field: str


@dataclass(frozen=True, slots=True)
class CurrentPortfolioValuationResult:
    """Current valuation outcome for one owned portfolio."""

    ledger: LedgerReplayResult
    provenance: CurrentValuationProvenance
    prices: tuple[CurrentPositionPrice, ...]
    warnings: tuple[CurrentValuationWarning, ...]
    is_complete: bool
    valuation: PortfolioValuationResult | None
    allocation: PortfolioAllocationResult | None


class TradingSessionCalendar(Protocol):
    """Provider-neutral boundary for recent exchange trading sessions."""

    def sessions_through(
        self,
        as_of_date: date,
        *,
        count: int,
    ) -> tuple[date, ...]:
        """Return ascending trading sessions ending on or before as_of_date."""


class MarketBarQueryExecutor(Protocol):
    """Provider-neutral application boundary for market-bar execution."""

    def __call__(
        self,
        query: NormalizedMarketBarQuery,
        *,
        resolver: AssetResolver,
        provider: MarketDataProvider,
    ) -> MarketBarBatchResult:
        """Execute one normalized market-bar query."""


def value_owned_portfolio(
    *,
    user: User,
    portfolio_id: UUID,
    as_of: datetime,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> CurrentPortfolioValuationResult:
    """Value one owned portfolio using ledger holdings and current raw closes."""
    portfolio = (
        Portfolio.objects.owned_by(user).select_related("benchmark_asset").get(id=portfolio_id)
    )
    ledger = replay_portfolio_ledger(
        portfolio,
        as_of=as_of,
    )

    if not ledger.positions:
        cash_only_valuation = value_portfolio(
            (),
            cash_value=_decimal_to_engine_float(
                ledger.cash_balance,
                field_name="cash_balance",
            ),
        )
        cash_only_allocation = _derive_allocation_if_positive(cash_only_valuation)

        return CurrentPortfolioValuationResult(
            ledger=ledger,
            provenance=CurrentValuationProvenance(
                portfolio_id=portfolio.id,
                benchmark_asset_id=portfolio.benchmark_asset_id,
                provider=provider_name,
                as_of=as_of,
                retrieved_at=None,
                price_field="close",
            ),
            prices=(),
            warnings=(),
            is_complete=True,
            valuation=cash_only_valuation,
            allocation=cash_only_allocation,
        )

    assets = _assets_for_ledger(ledger)
    symbols = tuple(assets[position.asset_id].symbol for position in ledger.positions)
    _reject_duplicate_symbols(symbols)

    sessions = _valuation_sessions(
        trading_calendar,
        as_of_date=as_of.date(),
    )
    query = normalize_market_bar_query(
        symbols,
        start=sessions[0],
        end=as_of.date() + timedelta(days=1),
        provider=provider_name,
    )
    batch = executor(
        query,
        resolver=resolver,
        provider=provider,
    )

    prices, warnings = _resolve_current_prices(
        ledger=ledger,
        assets=assets,
        batch=batch,
        sessions=sessions,
    )
    is_complete = len(prices) == len(ledger.positions)

    if not is_complete:
        valuation = None
        allocation = None
    else:
        valuation = _value_complete_portfolio(
            ledger=ledger,
            prices=prices,
        )
        allocation = _derive_allocation_if_positive(valuation)

    return CurrentPortfolioValuationResult(
        ledger=ledger,
        provenance=CurrentValuationProvenance(
            portfolio_id=portfolio.id,
            benchmark_asset_id=portfolio.benchmark_asset_id,
            provider=batch.meta.provider,
            as_of=as_of,
            retrieved_at=batch.meta.retrieved_at,
            price_field="close",
        ),
        prices=prices,
        warnings=warnings,
        is_complete=is_complete,
        valuation=valuation,
        allocation=allocation,
    )


def _assets_for_ledger(
    ledger: LedgerReplayResult,
) -> dict[UUID, Asset]:
    asset_ids = tuple(position.asset_id for position in ledger.positions)
    assets = Asset.objects.in_bulk(asset_ids)

    missing = tuple(asset_id for asset_id in asset_ids if asset_id not in assets)
    if missing:
        raise CurrentValuationError(f"Ledger references unknown asset IDs: {missing!r}.")

    return assets


def _reject_duplicate_symbols(
    symbols: Sequence[str],
) -> None:
    if len(set(symbols)) != len(symbols):
        raise CurrentValuationError(
            "Current valuation requires unique canonical symbols for held assets."
        )


def _valuation_sessions(
    trading_calendar: TradingSessionCalendar,
    *,
    as_of_date: date,
) -> tuple[date, ...]:
    required_count = MAX_STALE_PRICE_TRADING_SESSIONS + 2
    sessions = trading_calendar.sessions_through(
        as_of_date,
        count=required_count,
    )

    if len(sessions) != required_count:
        raise CurrentValuationError(
            f"Trading calendar must provide exactly {required_count} sessions."
        )

    if tuple(sorted(set(sessions))) != sessions:
        raise CurrentValuationError("Trading sessions must be unique and strictly ascending.")

    if sessions[-1] > as_of_date:
        raise CurrentValuationError("Trading sessions must not extend beyond the valuation date.")

    return sessions


def _resolve_current_prices(
    *,
    ledger: LedgerReplayResult,
    assets: dict[UUID, Asset],
    batch: MarketBarBatchResult,
    sessions: tuple[date, ...],
) -> tuple[
    tuple[CurrentPositionPrice, ...],
    tuple[CurrentValuationWarning, ...],
]:
    results_by_symbol = {result.symbol: result for result in batch.results}
    quantity_by_asset = {position.asset_id: position.quantity for position in ledger.positions}

    prices: list[CurrentPositionPrice] = []
    warnings: list[CurrentValuationWarning] = []

    for position in ledger.positions:
        asset = assets[position.asset_id]
        symbol_result = results_by_symbol.get(asset.symbol)

        if symbol_result is None:
            warnings.append(
                _warning(
                    code=CurrentValuationWarningCode.PRICE_NOT_FOUND,
                    asset=asset,
                    message=("No market-data result was returned for the held asset."),
                )
            )
            continue

        if symbol_result.status != MarketBarStatus.SUCCEEDED:
            warnings.append(
                _status_warning(
                    asset=asset,
                    status=symbol_result.status,
                )
            )
            continue

        bars = tuple(bar for bar in symbol_result.bars if bar.trade_date <= sessions[-1])
        if not bars:
            warnings.append(
                _warning(
                    code=CurrentValuationWarningCode.PRICE_NO_DATA,
                    asset=asset,
                    message=(
                        "Provider returned no usable raw-close observation "
                        "for the valuation window."
                    ),
                )
            )
            continue

        latest_bar = bars[-1]

        try:
            session_index = sessions.index(latest_bar.trade_date)
        except ValueError:
            warnings.append(
                _warning(
                    code=(CurrentValuationWarningCode.PRICE_DATE_OUTSIDE_SESSION_CALENDAR),
                    asset=asset,
                    message=(
                        "Latest price date is not present in the supplied trading-session calendar."
                    ),
                )
            )
            continue

        stale_sessions = len(sessions) - 1 - session_index

        if stale_sessions > MAX_STALE_PRICE_TRADING_SESSIONS:
            warnings.append(
                _warning(
                    code=CurrentValuationWarningCode.PRICE_TOO_STALE,
                    asset=asset,
                    message=(
                        "Latest raw-close price exceeds the configured "
                        f"{MAX_STALE_PRICE_TRADING_SESSIONS}-session "
                        "staleness limit."
                    ),
                )
            )
            continue

        if stale_sessions > 0:
            warnings.append(
                _warning(
                    code=CurrentValuationWarningCode.STALE_PRICE_USED,
                    asset=asset,
                    message=(
                        "Valuation uses a prior raw-close price that is "
                        f"{stale_sessions} trading session(s) stale."
                    ),
                )
            )

        prices.append(
            CurrentPositionPrice(
                asset_id=asset.id,
                symbol=asset.symbol,
                quantity=quantity_by_asset[asset.id],
                trade_date=latest_bar.trade_date,
                raw_close=Decimal(str(latest_bar.close)),
                stale_trading_sessions=stale_sessions,
            )
        )

    return tuple(prices), tuple(warnings)


def _status_warning(
    *,
    asset: Asset,
    status: MarketBarStatus,
) -> CurrentValuationWarning:
    if status == MarketBarStatus.NOT_FOUND:
        code = CurrentValuationWarningCode.PRICE_NOT_FOUND
        message = "Held asset could not be resolved for market-data valuation."
    elif status == MarketBarStatus.NO_DATA:
        code = CurrentValuationWarningCode.PRICE_NO_DATA
        message = "Provider returned no market data for the held asset."
    else:
        code = CurrentValuationWarningCode.PRICE_PROVIDER_FAILED
        message = "Provider failed to return a usable price for the held asset."

    return _warning(
        code=code,
        asset=asset,
        message=message,
    )


def _warning(
    *,
    code: CurrentValuationWarningCode,
    asset: Asset,
    message: str,
) -> CurrentValuationWarning:
    return CurrentValuationWarning(
        code=code,
        message=message,
        asset_id=asset.id,
        symbol=asset.symbol,
    )


def _value_complete_portfolio(
    *,
    ledger: LedgerReplayResult,
    prices: tuple[CurrentPositionPrice, ...],
) -> PortfolioValuationResult:
    price_by_asset = {price.asset_id: price for price in prices}

    inputs = tuple(
        AssetPositionValuationInput(
            asset_id=position.asset_id,
            quantity=_decimal_to_engine_float(
                position.quantity,
                field_name="quantity",
            ),
            valuation_price=_decimal_to_engine_float(
                price_by_asset[position.asset_id].raw_close,
                field_name="raw_close",
            ),
        )
        for position in ledger.positions
    )

    return value_portfolio(
        inputs,
        cash_value=_decimal_to_engine_float(
            ledger.cash_balance,
            field_name="cash_balance",
        ),
    )


def _derive_allocation_if_positive(
    valuation: PortfolioValuationResult,
) -> PortfolioAllocationResult | None:
    if valuation.total_market_value <= 0.0:
        return None

    if valuation.cash_value < 0.0:
        return None

    return derive_portfolio_allocation(valuation)


def _decimal_to_engine_float(
    value: Decimal,
    *,
    field_name: str,
) -> float:
    converted = float(value)

    if not math.isfinite(converted):
        raise CurrentValuationError(f"{field_name} cannot be represented as a finite engine value.")

    return converted
