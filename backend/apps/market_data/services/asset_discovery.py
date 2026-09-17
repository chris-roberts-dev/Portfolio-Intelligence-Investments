"""Application orchestration for live canonical asset discovery.

Discovery is deliberately separate from historical bar retrieval. Only symbols
that are unresolved for the already-selected provider are discovered and
persisted; the existing resolver/provider bar pipeline then runs unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID

from apps.market_data.contracts import (
    MarketBarBatchResult,
    MarketBarStatus,
    MarketBarSymbolResult,
    NormalizedMarketBarQuery,
)
from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.providers.discovery_base import (
    AssetDiscoveryIssue,
    AssetDiscoveryIssueCode,
    AssetDiscoveryProvider,
    DiscoveredProviderAsset,
)
from apps.market_data.services.asset_resolution import AssetResolver
from apps.market_data.services.market_bar_query import execute_market_bar_query
from portfolio_engine.config import MAX_BAR_QUERY_ROWS


class AssetCatalogWriteErrorCode(StrEnum):
    """Stable failures while turning discovered metadata into canonical identity."""

    PROVIDER_SYMBOL_CONFLICT = "PROVIDER_SYMBOL_CONFLICT"
    AMBIGUOUS_CANONICAL_ASSET = "AMBIGUOUS_CANONICAL_ASSET"
    EXISTING_CANONICAL_ASSET_UNSUPPORTED = "EXISTING_CANONICAL_ASSET_UNSUPPORTED"
    PERSISTENCE_VALIDATION_FAILED = "PERSISTENCE_VALIDATION_FAILED"


class AssetCatalogWriteError(ValueError):
    """Raised when discovered metadata cannot safely become canonical identity."""

    def __init__(
        self,
        code: AssetCatalogWriteErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@runtime_checkable
class AssetCatalogWriter(Protocol):
    """Persistence boundary for one discovered canonical asset."""

    def persist(
        self,
        discovered: DiscoveredProviderAsset,
        *,
        provider: str,
    ) -> UUID:
        """Persist/reuse canonical identity and return its internal asset UUID."""
        ...


@dataclass(frozen=True, slots=True)
class AssetDiscoveryDiagnostic:
    """Per-symbol diagnostic used only when discovery did not create a usable mapping."""

    symbol: str
    status: MarketBarStatus
    warning: str


class CanonicalAssetResolutionStatus(StrEnum):
    """Public resolution outcome for a user-entered symbol."""

    RESOLVED = "RESOLVED"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CanonicalAssetResolutionOutcome:
    """One ordered canonical asset-resolution/discovery outcome."""

    symbol: str
    status: CanonicalAssetResolutionStatus
    asset_id: UUID | None
    warning: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalAssetResolutionBatch:
    """Ordered resolution batch used by authenticated application APIs."""

    provider: str
    outcomes: tuple[CanonicalAssetResolutionOutcome, ...]


def resolve_canonical_assets_with_discovery(
    symbols: Sequence[str],
    *,
    provider_name: str,
    resolver: AssetResolver,
    discovery_provider: AssetDiscoveryProvider | None,
    catalog_writer: AssetCatalogWriter | None,
) -> CanonicalAssetResolutionBatch:
    """Resolve known assets and discover only unresolved supported symbols."""
    normalized_provider = provider_name.strip().lower()
    if not normalized_provider:
        raise ValueError("provider_name must not be blank.")

    initial = resolver.resolve(symbols, provider=normalized_provider)
    ordered_symbols = tuple(outcome.requested_symbol.symbol for outcome in initial.outcomes)
    diagnostics = _discover_and_persist_unresolved_assets(
        ordered_symbols,
        provider_name=normalized_provider,
        resolver=resolver,
        discovery_provider=discovery_provider,
        catalog_writer=catalog_writer,
    )
    final = resolver.resolve(ordered_symbols, provider=normalized_provider)
    resolved_by_symbol = {
        outcome.requested_symbol.symbol: outcome.asset_id for outcome in final.resolved
    }

    outcomes: list[CanonicalAssetResolutionOutcome] = []
    for symbol in ordered_symbols:
        asset_id = resolved_by_symbol.get(symbol)
        if asset_id is not None:
            outcomes.append(
                CanonicalAssetResolutionOutcome(
                    symbol=symbol,
                    status=CanonicalAssetResolutionStatus.RESOLVED,
                    asset_id=asset_id,
                )
            )
            continue

        diagnostic = diagnostics.get(symbol)
        if diagnostic is None or diagnostic.status is MarketBarStatus.NOT_FOUND:
            status = CanonicalAssetResolutionStatus.NOT_FOUND
        else:
            status = CanonicalAssetResolutionStatus.FAILED

        outcomes.append(
            CanonicalAssetResolutionOutcome(
                symbol=symbol,
                status=status,
                asset_id=None,
                warning=(diagnostic.warning if diagnostic is not None else None),
            )
        )

    return CanonicalAssetResolutionBatch(
        provider=normalized_provider,
        outcomes=tuple(outcomes),
    )


def execute_market_bar_query_with_discovery(
    query: NormalizedMarketBarQuery,
    *,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    discovery_provider: AssetDiscoveryProvider | None,
    catalog_writer: AssetCatalogWriter | None,
    max_rows: int = MAX_BAR_QUERY_ROWS,
) -> MarketBarBatchResult:
    """Discover unresolved supported symbols, then execute the canonical bar query."""
    diagnostics = _discover_and_persist_unresolved_assets(
        query.symbols,
        provider_name=provider.name,
        resolver=resolver,
        discovery_provider=discovery_provider,
        catalog_writer=catalog_writer,
    )

    result = execute_market_bar_query(
        query,
        resolver=resolver,
        provider=provider,
        max_rows=max_rows,
    )

    if not diagnostics:
        return result

    return MarketBarBatchResult(
        results=tuple(
            _apply_discovery_diagnostic(
                symbol_result,
                diagnostics=diagnostics,
            )
            for symbol_result in result.results
        ),
        meta=result.meta,
    )


def _discover_and_persist_unresolved_assets(
    symbols: Sequence[str],
    *,
    provider_name: str,
    resolver: AssetResolver,
    discovery_provider: AssetDiscoveryProvider | None,
    catalog_writer: AssetCatalogWriter | None,
) -> Mapping[str, AssetDiscoveryDiagnostic]:
    normalized_provider = provider_name.strip().lower()

    if not normalized_provider:
        raise ValueError("provider_name must not be blank.")

    initial_resolution = resolver.resolve(
        symbols,
        provider=normalized_provider,
    )
    unresolved_symbols = tuple(
        outcome.requested_symbol.symbol for outcome in initial_resolution.unresolved
    )

    if not unresolved_symbols or discovery_provider is None:
        return {}

    if catalog_writer is None:
        raise ValueError("catalog_writer is required when a discovery provider is configured.")

    if discovery_provider.name.strip().lower() != normalized_provider:
        raise ValueError("Asset discovery provider name must match the selected bar provider.")

    discovery_result = discovery_provider.discover(
        unresolved_symbols,
    )

    if discovery_result.provider != normalized_provider:
        raise ValueError("Asset discovery result provider must match the selected bar provider.")

    outcomes_by_symbol = {
        outcome.requested_symbol: outcome for outcome in discovery_result.outcomes
    }
    diagnostics: dict[str, AssetDiscoveryDiagnostic] = {}
    persisted_asset_ids: dict[str, UUID] = {}

    for symbol in unresolved_symbols:
        outcome = outcomes_by_symbol.get(symbol)

        if outcome is None:
            diagnostics[symbol] = AssetDiscoveryDiagnostic(
                symbol=symbol,
                status=MarketBarStatus.FAILED,
                warning=(f"Asset discovery provider returned no outcome for {symbol}."),
            )
            continue

        if isinstance(outcome, AssetDiscoveryIssue):
            diagnostics[symbol] = _diagnostic_for_issue(outcome)
            continue

        try:
            persisted_asset_ids[symbol] = catalog_writer.persist(
                outcome,
                provider=normalized_provider,
            )
        except AssetCatalogWriteError as exc:
            diagnostics[symbol] = AssetDiscoveryDiagnostic(
                symbol=symbol,
                status=MarketBarStatus.FAILED,
                warning=str(exc),
            )

    if persisted_asset_ids:
        persisted_resolution = resolver.resolve(
            tuple(persisted_asset_ids),
            provider=normalized_provider,
        )
        resolved_ids = {
            outcome.requested_symbol.symbol: outcome.asset_id
            for outcome in persisted_resolution.resolved
        }

        for symbol, expected_asset_id in persisted_asset_ids.items():
            actual_asset_id = resolved_ids.get(symbol)

            if actual_asset_id != expected_asset_id:
                diagnostics[symbol] = AssetDiscoveryDiagnostic(
                    symbol=symbol,
                    status=MarketBarStatus.FAILED,
                    warning=("Discovered canonical asset could not be resolved after persistence."),
                )

    return diagnostics


def _diagnostic_for_issue(
    issue: AssetDiscoveryIssue,
) -> AssetDiscoveryDiagnostic:
    status = (
        MarketBarStatus.NOT_FOUND
        if issue.code
        in {
            AssetDiscoveryIssueCode.NOT_FOUND,
            AssetDiscoveryIssueCode.UNSUPPORTED_ASSET_TYPE,
            AssetDiscoveryIssueCode.UNSUPPORTED_CURRENCY,
        }
        else MarketBarStatus.FAILED
    )

    return AssetDiscoveryDiagnostic(
        symbol=issue.requested_symbol,
        status=status,
        warning=issue.message,
    )


def _apply_discovery_diagnostic(
    result: MarketBarSymbolResult,
    *,
    diagnostics: Mapping[str, AssetDiscoveryDiagnostic],
) -> MarketBarSymbolResult:
    diagnostic = diagnostics.get(result.symbol)

    if diagnostic is None or result.status is not MarketBarStatus.NOT_FOUND:
        return result

    return MarketBarSymbolResult(
        symbol=result.symbol,
        asset_id=None,
        status=diagnostic.status,
        warnings=(diagnostic.warning,),
    )
