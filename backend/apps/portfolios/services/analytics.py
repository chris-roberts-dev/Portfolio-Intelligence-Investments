"""Owned-portfolio analytics application service.

This service composes ledger-derived daily performance, current valuation, the
provider-neutral market-data boundary, and the framework-independent
quantitative engine. It does not implement financial formulas itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from apps.accounts.models import User
from apps.assets.models import Asset
from apps.market_data.contracts import MarketBarStatus, normalize_market_bar_query
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.services.current_valuation import (
    MarketBarQueryExecutor,
    TradingSessionCalendar,
    value_owned_portfolio,
)
from apps.portfolios.services.daily_performance import (
    DailyPortfolioPerformanceResult,
    calculate_owned_portfolio_daily_performance,
)
from portfolio_engine.config import (
    DEFAULT_MAR_ANNUAL,
    DEFAULT_RISK_FREE_RATE,
    MIN_BETA_OBS,
    MIN_GENERAL_STAT_OBS,
    TRADING_DAYS_PER_YEAR,
)
from portfolio_engine.contracts.analytical_result import AnalyticalResultProvenance
from portfolio_engine.performance.downside import (
    SortinoRatioResult,
    sortino_ratio,
)
from portfolio_engine.performance.drawdown import (
    MaximumDrawdownResult,
    maximum_drawdown,
)
from portfolio_engine.performance.returns import (
    AnnualizedReturnResult,
    annualized_geometric_return,
    simple_returns,
)
from portfolio_engine.performance.statistics import (
    SharpeRatioResult,
    annualized_volatility,
    sharpe_ratio,
)
from portfolio_engine.portfolio.allocation import PortfolioAllocationResult
from portfolio_engine.risk.concentration import (
    ConcentrationResult,
    NormalizedPortfolioWeights,
    portfolio_concentration,
)
from portfolio_engine.risk.relationships import BetaResult, ReturnObservation, beta


class PortfolioAnalyticsError(ValueError):
    """Raised when analytics orchestration violates its application contract."""


class PortfolioAnalyticsWarningCode(StrEnum):
    """Stable warnings emitted by the portfolio analytics service."""

    SOURCE_WARNING = "SOURCE_WARNING"
    PERFORMANCE_UNAVAILABLE = "PERFORMANCE_UNAVAILABLE"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    UNDEFINED_CAGR = "UNDEFINED_CAGR"
    UNDEFINED_SHARPE = "UNDEFINED_SHARPE"
    UNDEFINED_SORTINO = "UNDEFINED_SORTINO"
    BENCHMARK_NOT_CONFIGURED = "BENCHMARK_NOT_CONFIGURED"
    BENCHMARK_NOT_FOUND = "BENCHMARK_NOT_FOUND"
    BENCHMARK_NO_DATA = "BENCHMARK_NO_DATA"
    BENCHMARK_PROVIDER_FAILED = "BENCHMARK_PROVIDER_FAILED"
    UNDEFINED_BETA = "UNDEFINED_BETA"
    CURRENT_VALUATION_INCOMPLETE = "CURRENT_VALUATION_INCOMPLETE"
    CURRENT_ALLOCATION_UNAVAILABLE = "CURRENT_ALLOCATION_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class PortfolioAnalyticsWarning:
    """One structured portfolio-analytics warning."""

    code: PortfolioAnalyticsWarningCode
    message: str
    observations: int | None = None


@dataclass(frozen=True, slots=True)
class PortfolioAnalyticsResult:
    """Canonical owned-portfolio analytics application result."""

    portfolio_id: UUID
    observations: int
    benchmark_observations: int | None
    cumulative_return: float | None
    cagr: AnnualizedReturnResult | None
    annualized_volatility: float | None
    sharpe: SharpeRatioResult | None
    sortino: SortinoRatioResult | None
    maximum_drawdown: MaximumDrawdownResult | None
    beta: BetaResult | None
    current_allocation: PortfolioAllocationResult | None
    concentration: ConcentrationResult | None
    provenance: AnalyticalResultProvenance
    warnings: tuple[PortfolioAnalyticsWarning, ...]


def analyze_owned_portfolio(
    *,
    user: User,
    portfolio_id: UUID,
    valuation_times: Sequence[datetime],
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    risk_free_rate_annual: float = DEFAULT_RISK_FREE_RATE,
    minimum_acceptable_return_annual: float = DEFAULT_MAR_ANNUAL,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> PortfolioAnalyticsResult:
    """Calculate the Phase 4 owned-portfolio analytics set.

    Historical return/risk metrics use the completed adjusted-close daily TWR
    series. Current allocation and concentration use the completed raw-close
    current valuation service. Benchmark beta uses adjusted-close benchmark
    returns aligned by exact period-end dates through the Phase 3 beta kernel.
    """
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
    current = value_owned_portfolio(
        user=user,
        portfolio_id=portfolio_id,
        as_of=valuation_times[-1],
        provider_name=provider_name,
        resolver=resolver,
        provider=provider,
        trading_calendar=trading_calendar,
        executor=executor,
    )

    warnings = [
        PortfolioAnalyticsWarning(
            code=PortfolioAnalyticsWarningCode.SOURCE_WARNING,
            message=warning.message,
        )
        for warning in performance.warnings
    ]

    cumulative_return: float | None = None
    cagr: AnnualizedReturnResult | None = None
    volatility: float | None = None
    sharpe: SharpeRatioResult | None = None
    sortino: SortinoRatioResult | None = None
    drawdown: MaximumDrawdownResult | None = None
    beta_result: BetaResult | None = None
    benchmark_observations: int | None = None

    daily_returns: tuple[float, ...] = ()
    portfolio_return_observations: tuple[ReturnObservation, ...] = ()

    if performance.twr is not None:
        cumulative_return = performance.twr.cumulative_return
        daily_returns = tuple(
            observation.simple_return for observation in performance.twr.daily_returns
        )
        portfolio_return_observations = tuple(
            ReturnObservation(
                trade_date=observation.valuation_date,
                value=observation.simple_return,
            )
            for observation in performance.twr.daily_returns
        )
        drawdown = maximum_drawdown(daily_returns)

        try:
            cagr = annualized_geometric_return(
                1.0 + cumulative_return,
                period_start=performance.twr.period_start,
                period_end=performance.twr.period_end,
            )
        except ValueError as exc:
            warnings.append(
                PortfolioAnalyticsWarning(
                    code=PortfolioAnalyticsWarningCode.UNDEFINED_CAGR,
                    message=str(exc),
                    observations=len(daily_returns),
                )
            )

        if len(daily_returns) < MIN_GENERAL_STAT_OBS:
            warnings.append(
                PortfolioAnalyticsWarning(
                    code=PortfolioAnalyticsWarningCode.INSUFFICIENT_HISTORY,
                    message=(
                        "Volatility, Sharpe, and Sortino require at least "
                        f"{MIN_GENERAL_STAT_OBS} daily return observations."
                    ),
                    observations=len(daily_returns),
                )
            )
        else:
            volatility = annualized_volatility(daily_returns)
            sharpe = sharpe_ratio(
                daily_returns,
                risk_free_rate_annual=risk_free_rate_annual,
            )
            sortino = sortino_ratio(
                daily_returns,
                minimum_acceptable_return_annual=(minimum_acceptable_return_annual),
            )
            _append_ratio_warnings(
                warnings,
                sharpe=sharpe,
                sortino=sortino,
            )

        (
            beta_result,
            benchmark_observations,
            benchmark_warnings,
            benchmark_symbol,
        ) = _calculate_beta(
            performance=performance,
            portfolio_returns=portfolio_return_observations,
            resolver=resolver,
            provider=provider,
            executor=executor,
        )
        warnings.extend(benchmark_warnings)
    else:
        warnings.append(
            PortfolioAnalyticsWarning(
                code=PortfolioAnalyticsWarningCode.PERFORMANCE_UNAVAILABLE,
                message=("Historical analytics are unavailable because daily TWR is undefined."),
                observations=0,
            )
        )
        benchmark_symbol = _benchmark_symbol(performance)

    allocation = current.allocation
    concentration: ConcentrationResult | None = None

    if not current.is_complete:
        warnings.append(
            PortfolioAnalyticsWarning(
                code=(PortfolioAnalyticsWarningCode.CURRENT_VALUATION_INCOMPLETE),
                message="Current portfolio valuation is incomplete.",
            )
        )

    if allocation is None:
        warnings.append(
            PortfolioAnalyticsWarning(
                code=(PortfolioAnalyticsWarningCode.CURRENT_ALLOCATION_UNAVAILABLE),
                message=(
                    "Current allocation is unavailable because total portfolio "
                    "value is non-positive or the valuation is incomplete."
                ),
            )
        )
    else:
        concentration = portfolio_concentration(
            NormalizedPortfolioWeights(
                security_weights=allocation.security_weights,
                cash_weight=allocation.cash_weight,
            )
        )

    assumptions = (
        "historical returns use adjusted_close",
        "current allocation uses raw close",
        "daily TWR treats DEPOSIT/WITHDRAWAL as external flows",
        f"risk_free_rate_annual={risk_free_rate_annual}",
        (f"minimum_acceptable_return_annual={minimum_acceptable_return_annual}"),
        f"minimum_general_stat_observations={MIN_GENERAL_STAT_OBS}",
        f"minimum_beta_observations={MIN_BETA_OBS}",
    )
    warning_messages = tuple(warning.message for warning in warnings)

    provenance = AnalyticalResultProvenance(
        as_of_date=valuation_times[-1].date(),
        period_start=performance.provenance.period_start,
        period_end=performance.provenance.period_end,
        data_source=performance.provenance.provider,
        price_field="adjusted_close",
        annualization_factor=float(TRADING_DAYS_PER_YEAR),
        benchmark=benchmark_symbol,
        assumptions=assumptions,
        warnings=warning_messages,
    )

    return PortfolioAnalyticsResult(
        portfolio_id=portfolio_id,
        observations=len(daily_returns),
        benchmark_observations=benchmark_observations,
        cumulative_return=cumulative_return,
        cagr=cagr,
        annualized_volatility=volatility,
        sharpe=sharpe,
        sortino=sortino,
        maximum_drawdown=drawdown,
        beta=beta_result,
        current_allocation=allocation,
        concentration=concentration,
        provenance=provenance,
        warnings=tuple(warnings),
    )


def _calculate_beta(
    *,
    performance: DailyPortfolioPerformanceResult,
    portfolio_returns: tuple[ReturnObservation, ...],
    resolver: AssetResolver,
    provider: MarketDataProvider,
    executor: MarketBarQueryExecutor,
) -> tuple[
    BetaResult | None,
    int | None,
    tuple[PortfolioAnalyticsWarning, ...],
    str | None,
]:
    benchmark_asset_id = performance.provenance.benchmark_asset_id

    if benchmark_asset_id is None:
        return (
            None,
            None,
            (
                PortfolioAnalyticsWarning(
                    code=(PortfolioAnalyticsWarningCode.BENCHMARK_NOT_CONFIGURED),
                    message="Portfolio has no configured benchmark asset.",
                ),
            ),
            None,
        )

    benchmark_asset = Asset.objects.get(id=benchmark_asset_id)
    query = normalize_market_bar_query(
        (benchmark_asset.symbol,),
        start=performance.provenance.period_start,
        end=performance.provenance.period_end + timedelta(days=1),
        provider=performance.provenance.provider,
    )
    batch = executor(
        query,
        resolver=resolver,
        provider=provider,
    )

    if batch.meta.provider != performance.provenance.provider:
        raise PortfolioAnalyticsError(
            "Portfolio and benchmark analytics must use one provider provenance."
        )

    symbol_result = next(
        (result for result in batch.results if result.symbol == benchmark_asset.symbol),
        None,
    )

    if symbol_result is None or symbol_result.status == MarketBarStatus.NOT_FOUND:
        return (
            None,
            0,
            (
                PortfolioAnalyticsWarning(
                    code=PortfolioAnalyticsWarningCode.BENCHMARK_NOT_FOUND,
                    message="Configured benchmark could not be resolved.",
                    observations=0,
                ),
            ),
            benchmark_asset.symbol,
        )

    if symbol_result.status == MarketBarStatus.NO_DATA:
        return (
            None,
            0,
            (
                PortfolioAnalyticsWarning(
                    code=PortfolioAnalyticsWarningCode.BENCHMARK_NO_DATA,
                    message="Configured benchmark has no data for the period.",
                    observations=0,
                ),
            ),
            benchmark_asset.symbol,
        )

    if symbol_result.status != MarketBarStatus.SUCCEEDED:
        return (
            None,
            0,
            (
                PortfolioAnalyticsWarning(
                    code=(PortfolioAnalyticsWarningCode.BENCHMARK_PROVIDER_FAILED),
                    message="Benchmark provider request failed.",
                    observations=0,
                ),
            ),
            benchmark_asset.symbol,
        )

    price_by_date: dict[date, float] = {}

    for bar in symbol_result.bars:
        if bar.adjusted_close is None:
            continue
        if not (
            performance.provenance.period_start
            <= bar.trade_date
            <= performance.provenance.period_end
        ):
            continue
        price_by_date[bar.trade_date] = bar.adjusted_close

    benchmark_returns = _benchmark_return_observations(
        performance=performance,
        price_by_date=price_by_date,
    )
    result = beta(
        portfolio_returns,
        benchmark_returns,
    )
    warnings: list[PortfolioAnalyticsWarning] = []

    if result.value is None:
        message = result.warnings[0].message if result.warnings else "Beta is undefined."
        warnings.append(
            PortfolioAnalyticsWarning(
                code=PortfolioAnalyticsWarningCode.UNDEFINED_BETA,
                message=message,
                observations=result.observations,
            )
        )

    return (
        result,
        len(benchmark_returns),
        tuple(warnings),
        benchmark_asset.symbol,
    )


def _benchmark_return_observations(
    *,
    performance: DailyPortfolioPerformanceResult,
    price_by_date: dict[date, float],
) -> tuple[ReturnObservation, ...]:
    if performance.twr is None:
        return ()

    prior_date = performance.twr.period_start
    observations: list[ReturnObservation] = []

    for portfolio_return in performance.twr.daily_returns:
        current_date = portfolio_return.valuation_date
        prior_price = price_by_date.get(prior_date)
        current_price = price_by_date.get(current_date)

        if prior_price is not None and current_price is not None:
            benchmark_return = simple_returns((float(prior_price), float(current_price)))[0]
            observations.append(
                ReturnObservation(
                    trade_date=current_date,
                    value=benchmark_return,
                )
            )

        prior_date = current_date

    return tuple(observations)


def _benchmark_symbol(
    performance: DailyPortfolioPerformanceResult,
) -> str | None:
    benchmark_asset_id = performance.provenance.benchmark_asset_id

    if benchmark_asset_id is None:
        return None

    return Asset.objects.only("symbol").get(id=benchmark_asset_id).symbol


def _append_ratio_warnings(
    warnings: list[PortfolioAnalyticsWarning],
    *,
    sharpe: SharpeRatioResult,
    sortino: SortinoRatioResult,
) -> None:
    if sharpe.value is None:
        message = sharpe.warnings[0].message if sharpe.warnings else "Sharpe ratio is undefined."
        warnings.append(
            PortfolioAnalyticsWarning(
                code=PortfolioAnalyticsWarningCode.UNDEFINED_SHARPE,
                message=message,
                observations=sharpe.observations,
            )
        )

    if sortino.value is None:
        message = sortino.warnings[0].message if sortino.warnings else "Sortino ratio is undefined."
        warnings.append(
            PortfolioAnalyticsWarning(
                code=PortfolioAnalyticsWarningCode.UNDEFINED_SORTINO,
                message=message,
                observations=sortino.observations,
            )
        )
