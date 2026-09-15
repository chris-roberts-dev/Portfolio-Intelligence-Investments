"""Display-ready P0 portfolio allocation for dashboard consumers.

Current quantities, prices, and cash come from the existing current-valuation
application service. Security and cash weights come from the existing
framework-independent allocation result; this service only groups those
authoritative weights by persisted MVP asset class.

The current persisted security taxonomy is exhaustive STOCK/ETF. No security
is silently grouped into "Other". Unsupported allocation dimensions are not
fabricated from symbols, names, exchanges, or provider metadata.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.utils import timezone

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from apps.portfolios.models import Portfolio
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
from portfolio_engine.config import WEIGHT_SUM_TOLERANCE

ZERO = Decimal("0")

ALLOCATION_GROUPING_DIMENSION = "ASSET_CLASS"
SUPPORTED_ALLOCATION_GROUPING_DIMENSIONS = (ALLOCATION_GROUPING_DIMENSION,)

ALLOCATION_ORDERING_RULE = "SECURITY_WEIGHT_DESC_THEN_GROUP_KEY_CASH_LAST_V1"

OTHER_GROUPING_RULE = (
    "No Other aggregation is applied in the MVP because persisted security "
    "asset types are exhaustively constrained to STOCK and ETF."
)

_ASSET_TYPE_LABELS = {
    AssetType.STOCK: "Stocks",
    AssetType.ETF: "ETFs",
}


class DashboardAllocationError(ValueError):
    """Raised when dashboard allocation cannot satisfy its contract."""


class DashboardAllocationUnavailableReason(StrEnum):
    """Stable reason authoritative allocation weights are unavailable."""

    CURRENT_VALUATION_INCOMPLETE = "CURRENT_VALUATION_INCOMPLETE"
    CURRENT_ALLOCATION_UNAVAILABLE = "CURRENT_ALLOCATION_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class DashboardAllocationGroup:
    """One display-ready allocation group."""

    key: str
    label: str
    is_cash: bool
    asset_count: int
    market_value: Decimal
    weight: float | None


@dataclass(frozen=True, slots=True)
class DashboardAllocationTotals:
    """Exact allocation totals plus authoritative kernel weights."""

    total_market_value: Decimal | None
    invested_value: Decimal | None
    cash_value: Decimal
    invested_weight: float | None
    cash_weight: float | None


@dataclass(frozen=True, slots=True)
class DashboardAllocationProvenance:
    """Current valuation and grouping provenance."""

    portfolio_id: UUID
    base_currency: str
    provider: str
    as_of: datetime
    data_as_of: datetime | None
    calculated_at: datetime
    price_field: str
    grouping_dimension: str
    supported_grouping_dimensions: tuple[str, ...]
    grouping_source: str
    ordering_rule: str
    other_grouping_applied: bool
    other_grouping_threshold: float | None
    other_grouping_rule: str
    weight_sum_tolerance: float


@dataclass(frozen=True, slots=True)
class DashboardAllocationResult:
    """Complete P0 dashboard allocation response."""

    allocation_available: bool
    groups: tuple[DashboardAllocationGroup, ...]
    totals: DashboardAllocationTotals
    data_quality: PerformanceDataQualityState
    unavailable_reason: DashboardAllocationUnavailableReason | None
    warnings: tuple[str, ...]
    provenance: DashboardAllocationProvenance


def build_owned_portfolio_dashboard_allocation(
    *,
    user: User,
    portfolio_id: UUID,
    provider_name: str,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    trading_calendar: TradingSessionCalendar,
    calculated_at: datetime,
    executor: MarketBarQueryExecutor = execute_market_bar_query,
) -> DashboardAllocationResult:
    """Build current asset-class allocation using authoritative kernel weights."""
    if timezone.is_naive(calculated_at):
        raise DashboardAllocationError("calculated_at must be timezone-aware")

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

    warnings = tuple(warning.message for warning in current.warnings)

    if not current.is_complete:
        return DashboardAllocationResult(
            allocation_available=False,
            groups=(),
            totals=DashboardAllocationTotals(
                total_market_value=None,
                invested_value=None,
                cash_value=current.ledger.cash_balance,
                invested_weight=None,
                cash_weight=None,
            ),
            data_quality=PerformanceDataQualityState.PARTIAL,
            unavailable_reason=(DashboardAllocationUnavailableReason.CURRENT_VALUATION_INCOMPLETE),
            warnings=warnings,
            provenance=_provenance(
                portfolio=portfolio,
                current=current,
                calculated_at=calculated_at,
            ),
        )

    exact_values = _exact_position_values(current)
    invested_value = sum(
        exact_values.values(),
        ZERO,
    )
    total_market_value = invested_value + current.ledger.cash_balance

    if current.allocation is None:
        return DashboardAllocationResult(
            allocation_available=False,
            groups=_groups_without_weights(
                current=current,
                exact_values=exact_values,
            ),
            totals=DashboardAllocationTotals(
                total_market_value=total_market_value,
                invested_value=invested_value,
                cash_value=current.ledger.cash_balance,
                invested_weight=None,
                cash_weight=None,
            ),
            data_quality=PerformanceDataQualityState.UNAVAILABLE,
            unavailable_reason=(
                DashboardAllocationUnavailableReason.CURRENT_ALLOCATION_UNAVAILABLE
            ),
            warnings=warnings,
            provenance=_provenance(
                portfolio=portfolio,
                current=current,
                calculated_at=calculated_at,
            ),
        )

    groups = _groups_with_authoritative_weights(
        current=current,
        exact_values=exact_values,
    )
    invested_weight = math.fsum(allocation.weight for allocation in current.allocation.positions)
    grouped_weight_sum = math.fsum(group.weight for group in groups if group.weight is not None)

    if not math.isclose(
        grouped_weight_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=current.allocation.weight_sum_tolerance,
    ):
        raise DashboardAllocationError(
            "Grouped allocation weights must reconcile to one within "
            "the authoritative allocation tolerance."
        )

    return DashboardAllocationResult(
        allocation_available=True,
        groups=groups,
        totals=DashboardAllocationTotals(
            total_market_value=total_market_value,
            invested_value=invested_value,
            cash_value=current.ledger.cash_balance,
            invested_weight=invested_weight,
            cash_weight=current.allocation.cash_weight,
        ),
        data_quality=_complete_quality(current),
        unavailable_reason=None,
        warnings=warnings,
        provenance=_provenance(
            portfolio=portfolio,
            current=current,
            calculated_at=calculated_at,
        ),
    )


def _exact_position_values(
    current: CurrentPortfolioValuationResult,
) -> dict[UUID, Decimal]:
    values = {price.asset_id: price.quantity * price.raw_close for price in current.prices}
    ledger_asset_ids = {position.asset_id for position in current.ledger.positions}

    if set(values) != ledger_asset_ids:
        raise DashboardAllocationError(
            "Complete current valuation must have exactly one price for every ledger position."
        )

    return values


def _assets_for_values(
    exact_values: dict[UUID, Decimal],
) -> dict[UUID, Asset]:
    assets = Asset.objects.in_bulk(exact_values)

    missing = tuple(
        asset_id
        for asset_id in sorted(
            exact_values,
            key=lambda value: value.hex,
        )
        if asset_id not in assets
    )

    if missing:
        raise DashboardAllocationError(f"Allocation references unknown asset IDs: {missing!r}.")

    return assets


def _groups_with_authoritative_weights(
    *,
    current: CurrentPortfolioValuationResult,
    exact_values: dict[UUID, Decimal],
) -> tuple[DashboardAllocationGroup, ...]:
    if current.allocation is None:
        raise DashboardAllocationError("Authoritative allocation is required.")

    assets = _assets_for_values(exact_values)
    weight_by_asset = {
        allocation.asset_id: allocation.weight for allocation in current.allocation.positions
    }

    if set(weight_by_asset) != set(exact_values):
        raise DashboardAllocationError(
            "Allocation positions and valued positions must align exactly."
        )

    security_groups = _security_groups(
        assets=assets,
        exact_values=exact_values,
        weight_by_asset=weight_by_asset,
    )

    ordered_security_groups = tuple(
        sorted(
            security_groups,
            key=lambda group: (
                -_required_weight(group),
                group.key,
            ),
        )
    )

    cash_group = DashboardAllocationGroup(
        key="CASH",
        label="Cash",
        is_cash=True,
        asset_count=0,
        market_value=current.ledger.cash_balance,
        weight=current.allocation.cash_weight,
    )

    return (
        *ordered_security_groups,
        cash_group,
    )


def _groups_without_weights(
    *,
    current: CurrentPortfolioValuationResult,
    exact_values: dict[UUID, Decimal],
) -> tuple[DashboardAllocationGroup, ...]:
    assets = _assets_for_values(exact_values)
    security_groups = _security_groups(
        assets=assets,
        exact_values=exact_values,
        weight_by_asset=None,
    )
    ordered_security_groups = tuple(
        sorted(
            security_groups,
            key=lambda group: (
                -group.market_value,
                group.key,
            ),
        )
    )

    return (
        *ordered_security_groups,
        DashboardAllocationGroup(
            key="CASH",
            label="Cash",
            is_cash=True,
            asset_count=0,
            market_value=current.ledger.cash_balance,
            weight=None,
        ),
    )


def _security_groups(
    *,
    assets: dict[UUID, Asset],
    exact_values: dict[UUID, Decimal],
    weight_by_asset: dict[UUID, float] | None,
) -> tuple[DashboardAllocationGroup, ...]:
    grouped_values: dict[AssetType, Decimal] = {}
    grouped_weights: dict[AssetType, list[float]] = {}
    grouped_counts: dict[AssetType, int] = {}

    for asset_id, market_value in exact_values.items():
        try:
            asset_type = AssetType(assets[asset_id].asset_type)
        except ValueError as exc:
            raise DashboardAllocationError(
                f"Unsupported persisted asset type {assets[asset_id].asset_type!r}."
            ) from exc

        grouped_values[asset_type] = grouped_values.get(asset_type, ZERO) + market_value
        grouped_counts[asset_type] = grouped_counts.get(asset_type, 0) + 1

        if weight_by_asset is not None:
            grouped_weights.setdefault(
                asset_type,
                [],
            ).append(weight_by_asset[asset_id])

    return tuple(
        DashboardAllocationGroup(
            key=asset_type.value,
            label=_ASSET_TYPE_LABELS[asset_type],
            is_cash=False,
            asset_count=grouped_counts[asset_type],
            market_value=grouped_values[asset_type],
            weight=(
                math.fsum(grouped_weights[asset_type]) if weight_by_asset is not None else None
            ),
        )
        for asset_type in sorted(
            grouped_values,
            key=lambda value: value.value,
        )
    )


def _required_weight(
    group: DashboardAllocationGroup,
) -> float:
    if group.weight is None:
        raise DashboardAllocationError(f"Allocation group {group.key} has no authoritative weight.")

    return group.weight


def _complete_quality(
    current: CurrentPortfolioValuationResult,
) -> PerformanceDataQualityState:
    if any(
        warning.code is CurrentValuationWarningCode.STALE_PRICE_USED for warning in current.warnings
    ):
        return PerformanceDataQualityState.STALE

    return PerformanceDataQualityState.CURRENT


def _provenance(
    *,
    portfolio: Portfolio,
    current: CurrentPortfolioValuationResult,
    calculated_at: datetime,
) -> DashboardAllocationProvenance:
    return DashboardAllocationProvenance(
        portfolio_id=portfolio.id,
        base_currency=portfolio.base_currency,
        provider=current.provenance.provider,
        as_of=current.provenance.as_of,
        data_as_of=current.provenance.retrieved_at,
        calculated_at=calculated_at,
        price_field="close",
        grouping_dimension=ALLOCATION_GROUPING_DIMENSION,
        supported_grouping_dimensions=(SUPPORTED_ALLOCATION_GROUPING_DIMENSIONS),
        grouping_source="Asset.asset_type",
        ordering_rule=ALLOCATION_ORDERING_RULE,
        other_grouping_applied=False,
        other_grouping_threshold=None,
        other_grouping_rule=OTHER_GROUPING_RULE,
        weight_sum_tolerance=WEIGHT_SUM_TOLERANCE,
    )
