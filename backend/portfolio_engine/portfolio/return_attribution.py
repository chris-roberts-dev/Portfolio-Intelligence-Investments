"""Framework-independent actual-portfolio return attribution.

Dashboard visualization requirements reference: Section 11.2.
Canonical portfolio TWR reference: development guide Section 10.4.

For each period, one asset's investment P&L is defined as::

    ending_market_value - starting_market_value + internal_cash_flow

``internal_cash_flow`` is the signed ledger cash movement attributable to that
asset during the period: BUY is negative, SELL is positive, DIVIDEND is
positive, and transaction fees are already reflected in BUY/SELL cash movement.
External DEPOSIT/WITHDRAWAL cash flows are excluded.

Daily asset contribution is that P&L divided by prior portfolio value. Any
remaining difference from canonical daily portfolio TWR is kept as explicit
unattributed contribution rather than silently assigned to a security.

Selected-period contributions use exact wealth linking: each day's contribution
is scaled by portfolio wealth accumulated strictly before that day. Therefore
asset contributions plus unattributed contribution reconcile to chain-linked
portfolio TWR without using future observations.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from numbers import Real
from uuid import UUID


class ReturnAttributionError(ValueError):
    """Raised when return-attribution inputs violate the canonical contract."""


@dataclass(frozen=True, slots=True)
class AssetPeriodValueChange:
    """One asset's boundary values and signed internal cash flow for a period."""

    asset_id: UUID
    starting_market_value: float
    ending_market_value: float
    internal_cash_flow: float = 0.0

    def __post_init__(self) -> None:
        starting_value = _finite_real(
            self.starting_market_value,
            field_name="starting_market_value",
        )
        ending_value = _finite_real(
            self.ending_market_value,
            field_name="ending_market_value",
        )
        internal_cash_flow = _finite_real(
            self.internal_cash_flow,
            field_name="internal_cash_flow",
        )

        if starting_value < 0.0:
            raise ValueError("starting_market_value must not be negative")

        if ending_value < 0.0:
            raise ValueError("ending_market_value must not be negative")

        object.__setattr__(
            self,
            "starting_market_value",
            starting_value,
        )
        object.__setattr__(
            self,
            "ending_market_value",
            ending_value,
        )
        object.__setattr__(
            self,
            "internal_cash_flow",
            internal_cash_flow,
        )


@dataclass(frozen=True, slots=True)
class DailyAssetReturnContribution:
    """One asset's P&L and arithmetic contribution for one portfolio period."""

    asset_id: UUID
    profit_loss: float
    contribution: float


@dataclass(frozen=True, slots=True)
class DailyReturnAttributionResult:
    """One daily return decomposed into asset plus residual contribution."""

    period_start: date
    period_end: date
    prior_portfolio_value: float
    portfolio_return: float
    asset_contributions: tuple[DailyAssetReturnContribution, ...]
    asset_contribution_total: float
    unattributed_contribution: float
    reconciliation_error: float


@dataclass(frozen=True, slots=True)
class LinkedAssetReturnContribution:
    """One asset's wealth-linked contribution over the selected period."""

    asset_id: UUID
    contribution: float


@dataclass(frozen=True, slots=True)
class LinkedReturnAttributionResult:
    """Wealth-linked selected-period attribution reconciling to portfolio TWR."""

    period_start: date
    period_end: date
    periods: int
    cumulative_return: float
    asset_contributions: tuple[LinkedAssetReturnContribution, ...]
    asset_contribution_total: float
    unattributed_contribution: float
    reconciliation_error: float


def attribute_daily_portfolio_return(
    *,
    period_start: date,
    period_end: date,
    prior_portfolio_value: float,
    portfolio_return: float,
    assets: Sequence[AssetPeriodValueChange],
) -> DailyReturnAttributionResult:
    """Attribute one canonical daily portfolio return to asset P&L.

    Asset order does not affect the result. Output asset contributions are
    deterministically ordered by internal UUID identity.
    """
    if period_start >= period_end:
        raise ReturnAttributionError("period_start must be earlier than period_end")

    prior_value = _finite_real(
        prior_portfolio_value,
        field_name="prior_portfolio_value",
    )
    normalized_portfolio_return = _finite_real(
        portfolio_return,
        field_name="portfolio_return",
    )

    if prior_value <= 0.0:
        raise ReturnAttributionError("prior_portfolio_value must be positive")

    if normalized_portfolio_return < -1.0:
        raise ReturnAttributionError("portfolio_return must be greater than or equal to -1")

    observations = tuple(assets)
    asset_ids = tuple(observation.asset_id for observation in observations)

    if len(set(asset_ids)) != len(asset_ids):
        raise ReturnAttributionError("assets must not contain duplicate asset IDs")

    contributions = tuple(
        sorted(
            (
                _asset_contribution(
                    observation,
                    prior_portfolio_value=prior_value,
                )
                for observation in observations
            ),
            key=lambda observation: observation.asset_id.hex,
        )
    )
    asset_total = math.fsum(observation.contribution for observation in contributions)
    unattributed = normalized_portfolio_return - asset_total
    reconciliation_error = normalized_portfolio_return - math.fsum(
        (
            asset_total,
            unattributed,
        )
    )

    return DailyReturnAttributionResult(
        period_start=period_start,
        period_end=period_end,
        prior_portfolio_value=prior_value,
        portfolio_return=normalized_portfolio_return,
        asset_contributions=contributions,
        asset_contribution_total=asset_total,
        unattributed_contribution=unattributed,
        reconciliation_error=reconciliation_error,
    )


def link_daily_return_attributions(
    daily_results: Sequence[DailyReturnAttributionResult],
) -> LinkedReturnAttributionResult:
    """Wealth-link daily contributions into selected-period TWR contribution.

    If ``C_(i,t)`` is an asset's daily arithmetic contribution and
    ``W_(t-1)`` is portfolio wealth before period ``t``, linked contribution
    is::

        linked_i = sum(W_(t-1) * C_(i,t))

    with ``W_t = W_(t-1) * (1 + r_t)`` and ``W_0 = 1``.
    """
    results = tuple(daily_results)

    if not results:
        raise ReturnAttributionError("at least one daily attribution result is required")

    for index, result in enumerate(results):
        if not isinstance(
            result,
            DailyReturnAttributionResult,
        ):
            raise TypeError(f"daily_results[{index}] must be a DailyReturnAttributionResult")

    for previous, current in zip(
        results,
        results[1:],
        strict=False,
    ):
        if previous.period_end != current.period_start:
            raise ReturnAttributionError(
                "daily attribution periods must be contiguous by valuation boundary"
            )

    wealth = 1.0
    linked_by_asset: dict[UUID, float] = {}
    linked_unattributed = 0.0

    for result in results:
        wealth_before = wealth

        for contribution in result.asset_contributions:
            linked_by_asset[contribution.asset_id] = math.fsum(
                (
                    linked_by_asset.get(
                        contribution.asset_id,
                        0.0,
                    ),
                    wealth_before * contribution.contribution,
                )
            )

        linked_unattributed = math.fsum(
            (
                linked_unattributed,
                wealth_before * result.unattributed_contribution,
            )
        )
        wealth *= 1.0 + result.portfolio_return

        if not math.isfinite(wealth):
            raise ReturnAttributionError("linked portfolio wealth must remain finite")

    linked_assets = tuple(
        LinkedAssetReturnContribution(
            asset_id=asset_id,
            contribution=contribution,
        )
        for asset_id, contribution in sorted(
            linked_by_asset.items(),
            key=lambda item: item[0].hex,
        )
    )
    asset_total = math.fsum(observation.contribution for observation in linked_assets)
    cumulative_return = wealth - 1.0
    reconciliation_error = cumulative_return - math.fsum(
        (
            asset_total,
            linked_unattributed,
        )
    )

    return LinkedReturnAttributionResult(
        period_start=results[0].period_start,
        period_end=results[-1].period_end,
        periods=len(results),
        cumulative_return=cumulative_return,
        asset_contributions=linked_assets,
        asset_contribution_total=asset_total,
        unattributed_contribution=linked_unattributed,
        reconciliation_error=reconciliation_error,
    )


def _asset_contribution(
    observation: AssetPeriodValueChange,
    *,
    prior_portfolio_value: float,
) -> DailyAssetReturnContribution:
    if not isinstance(
        observation,
        AssetPeriodValueChange,
    ):
        raise TypeError("assets must contain only AssetPeriodValueChange values")

    profit_loss = math.fsum(
        (
            observation.ending_market_value,
            -observation.starting_market_value,
            observation.internal_cash_flow,
        )
    )
    contribution = profit_loss / prior_portfolio_value

    if not math.isfinite(contribution):
        raise ReturnAttributionError("asset return contribution must be finite")

    return DailyAssetReturnContribution(
        asset_id=observation.asset_id,
        profit_loss=profit_loss,
        contribution=contribution,
    )


def _finite_real(
    value: object,
    *,
    field_name: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{field_name} must be a real number")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")

    return number
