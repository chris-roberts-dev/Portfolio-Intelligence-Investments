"""Provider-neutral asset and provider-symbol resolution contracts.

Development guide references: Sections 8.2, 9.1, and 9.2.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol, runtime_checkable
from uuid import UUID

from apps.market_data.providers.base import ResolvedProviderAsset


class AssetResolutionErrorCode(StrEnum):
    """Stable failures for deterministic asset-resolution configuration."""

    BLANK_SYMBOL = "BLANK_SYMBOL"
    BLANK_PROVIDER = "BLANK_PROVIDER"
    DUPLICATE_CATALOG_RECORD = "DUPLICATE_CATALOG_RECORD"


class AssetResolutionError(ValueError):
    """Raised when symbol-resolution input or catalog configuration is invalid."""

    def __init__(
        self,
        code: AssetResolutionErrorCode,
        message: str,
        *,
        symbol: str | None = None,
        provider: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.symbol = symbol
        self.provider = provider


class UnresolvedAssetReason(StrEnum):
    """Canonical unresolved-symbol outcomes at the resolution boundary."""

    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class CanonicalUserSymbol:
    """One canonicalized user-entered symbol."""

    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.strip().upper():
            raise ValueError(
                "CanonicalUserSymbol must contain a non-blank trimmed uppercase symbol."
            )


@dataclass(frozen=True, slots=True)
class AssetProviderSymbolRecord:
    """Deterministic catalog record mapping one asset to one provider symbol."""

    asset_id: UUID
    canonical_symbol: str
    provider: str
    provider_symbol: str

    def __post_init__(self) -> None:
        if (
            not self.canonical_symbol
            or self.canonical_symbol != self.canonical_symbol.strip().upper()
        ):
            raise ValueError("canonical_symbol must be a non-blank trimmed uppercase symbol.")

        if not self.provider or self.provider != self.provider.strip().lower():
            raise ValueError("provider must be a non-blank trimmed lowercase name.")

        if not self.provider_symbol.strip():
            raise ValueError("provider_symbol must not be blank.")


@dataclass(frozen=True, slots=True)
class ResolvedAssetSymbol:
    """Successful canonical-symbol resolution for one requested symbol."""

    requested_symbol: CanonicalUserSymbol
    asset_id: UUID
    canonical_symbol: str
    provider_symbol: str

    def __post_init__(self) -> None:
        if self.canonical_symbol != self.requested_symbol.symbol:
            raise ValueError("Resolved canonical_symbol must exactly match the requested symbol.")

        if not self.provider_symbol.strip():
            raise ValueError("provider_symbol must not be blank.")

    @property
    def provider_asset(self) -> ResolvedProviderAsset:
        """Return the provider-call-safe internal identity."""
        return ResolvedProviderAsset(
            asset_id=self.asset_id,
            canonical_symbol=self.canonical_symbol,
            provider_symbol=self.provider_symbol,
        )


@dataclass(frozen=True, slots=True)
class UnresolvedAssetSymbol:
    """Explicit unresolved outcome for one canonicalized user symbol."""

    requested_symbol: CanonicalUserSymbol
    reason: UnresolvedAssetReason = UnresolvedAssetReason.NOT_FOUND


type AssetResolutionOutcome = ResolvedAssetSymbol | UnresolvedAssetSymbol


@dataclass(frozen=True, slots=True)
class AssetResolutionResult:
    """Ordered resolution outcomes for one provider."""

    provider: str
    outcomes: tuple[AssetResolutionOutcome, ...]

    @property
    def resolved(self) -> tuple[ResolvedAssetSymbol, ...]:
        """Return successfully resolved outcomes in request order."""
        return tuple(
            outcome for outcome in self.outcomes if isinstance(outcome, ResolvedAssetSymbol)
        )

    @property
    def unresolved(self) -> tuple[UnresolvedAssetSymbol, ...]:
        """Return unresolved outcomes in request order."""
        return tuple(
            outcome for outcome in self.outcomes if isinstance(outcome, UnresolvedAssetSymbol)
        )

    @property
    def provider_assets(self) -> tuple[ResolvedProviderAsset, ...]:
        """Return only resolved assets suitable for provider calls."""
        return tuple(outcome.provider_asset for outcome in self.resolved)


@runtime_checkable
class AssetResolver(Protocol):
    """Provider-neutral asset-resolution service boundary."""

    def resolve(
        self,
        symbols: Sequence[str],
        *,
        provider: str,
    ) -> AssetResolutionResult:
        """Resolve user symbols for exactly one provider."""
        ...


def canonicalize_user_symbols(
    symbols: Sequence[str],
) -> tuple[CanonicalUserSymbol, ...]:
    """Trim, uppercase, and de-duplicate symbols while preserving first order."""
    canonical_symbols: list[CanonicalUserSymbol] = []
    seen_symbols: set[str] = set()

    for raw_symbol in symbols:
        canonical_symbol = raw_symbol.strip().upper()

        if not canonical_symbol:
            raise AssetResolutionError(
                AssetResolutionErrorCode.BLANK_SYMBOL,
                "User-entered symbols must not be blank.",
                symbol=canonical_symbol,
            )

        if canonical_symbol not in seen_symbols:
            seen_symbols.add(canonical_symbol)
            canonical_symbols.append(CanonicalUserSymbol(canonical_symbol))

    return tuple(canonical_symbols)


class InMemoryAssetResolver:
    """Deterministic resolver backed by immutable provider-symbol catalog records."""

    def __init__(
        self,
        records: Sequence[AssetProviderSymbolRecord],
    ) -> None:
        index: dict[tuple[str, str], AssetProviderSymbolRecord] = {}

        for record in records:
            key = (record.provider, record.canonical_symbol)

            if key in index:
                raise AssetResolutionError(
                    AssetResolutionErrorCode.DUPLICATE_CATALOG_RECORD,
                    (
                        "Duplicate asset-resolution record for "
                        f"provider={record.provider!r}, "
                        f"canonical_symbol={record.canonical_symbol!r}."
                    ),
                    symbol=record.canonical_symbol,
                    provider=record.provider,
                )

            index[key] = record

        self._index = MappingProxyType(index)

    def resolve(
        self,
        symbols: Sequence[str],
        *,
        provider: str,
    ) -> AssetResolutionResult:
        """Resolve canonical symbols without rewriting them into other securities."""
        normalized_provider = provider.strip().lower()

        if not normalized_provider:
            raise AssetResolutionError(
                AssetResolutionErrorCode.BLANK_PROVIDER,
                "provider must not be blank.",
                provider=normalized_provider,
            )

        requested_symbols = canonicalize_user_symbols(symbols)
        outcomes: list[AssetResolutionOutcome] = []

        for requested_symbol in requested_symbols:
            record = self._index.get((normalized_provider, requested_symbol.symbol))

            if record is None:
                outcomes.append(
                    UnresolvedAssetSymbol(
                        requested_symbol=requested_symbol,
                    )
                )
                continue

            outcomes.append(
                ResolvedAssetSymbol(
                    requested_symbol=requested_symbol,
                    asset_id=record.asset_id,
                    canonical_symbol=record.canonical_symbol,
                    provider_symbol=record.provider_symbol,
                )
            )

        return AssetResolutionResult(
            provider=normalized_provider,
            outcomes=tuple(outcomes),
        )
