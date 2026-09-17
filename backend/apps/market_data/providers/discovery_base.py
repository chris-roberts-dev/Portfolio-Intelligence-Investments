"""Provider-neutral asset-discovery contracts.

This boundary exists so live symbol discovery can remain separate from both
canonical persistence and historical bar retrieval. Provider-specific SDK
loading belongs only in dedicated provider adapters.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class DiscoveredAssetType(StrEnum):
    """Supported canonical asset types returned by discovery adapters."""

    STOCK = "STOCK"
    ETF = "ETF"


class AssetDiscoveryIssueCode(StrEnum):
    """Stable per-symbol discovery outcomes that do not create canonical assets."""

    NOT_FOUND = "NOT_FOUND"
    UNSUPPORTED_ASSET_TYPE = "UNSUPPORTED_ASSET_TYPE"
    UNSUPPORTED_CURRENCY = "UNSUPPORTED_CURRENCY"
    INVALID_METADATA = "INVALID_METADATA"
    PROVIDER_ERROR = "PROVIDER_ERROR"


@dataclass(frozen=True, slots=True)
class DiscoveredProviderAsset:
    """Provider metadata sufficient to establish one canonical security identity."""

    requested_symbol: str
    canonical_symbol: str
    provider_symbol: str
    name: str
    asset_type: DiscoveredAssetType
    exchange: str
    currency: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("requested_symbol", self.requested_symbol),
            ("canonical_symbol", self.canonical_symbol),
        ):
            if not value or value != value.strip().upper():
                raise ValueError(f"{field_name} must be a non-blank trimmed uppercase symbol.")

        if self.canonical_symbol != self.requested_symbol:
            raise ValueError("Discovered canonical_symbol must exactly match requested_symbol.")

        if not self.provider_symbol.strip():
            raise ValueError("provider_symbol must not be blank.")

        if not self.name.strip():
            raise ValueError("name must not be blank.")

        if not self.exchange.strip():
            raise ValueError("exchange must not be blank.")

        if self.currency != self.currency.strip().upper() or len(self.currency) != 3:
            raise ValueError("currency must be a three-letter uppercase code.")


@dataclass(frozen=True, slots=True)
class AssetDiscoveryIssue:
    """Explicit provider discovery failure for one requested symbol."""

    requested_symbol: str
    code: AssetDiscoveryIssueCode
    message: str

    def __post_init__(self) -> None:
        if (
            not self.requested_symbol
            or self.requested_symbol != self.requested_symbol.strip().upper()
        ):
            raise ValueError("requested_symbol must be a non-blank trimmed uppercase symbol.")

        if not self.message.strip():
            raise ValueError("message must not be blank.")


type AssetDiscoveryOutcome = DiscoveredProviderAsset | AssetDiscoveryIssue


@dataclass(frozen=True, slots=True)
class AssetDiscoveryResult:
    """Ordered discovery results for exactly one provider."""

    provider: str
    outcomes: tuple[AssetDiscoveryOutcome, ...]

    def __post_init__(self) -> None:
        if not self.provider or self.provider != self.provider.strip().lower():
            raise ValueError("provider must be a non-blank trimmed lowercase name.")

        seen: set[str] = set()

        for outcome in self.outcomes:
            symbol = outcome.requested_symbol

            if symbol in seen:
                raise ValueError(f"Asset discovery returned duplicate outcome for {symbol!r}.")

            seen.add(symbol)


@runtime_checkable
class AssetDiscoveryProvider(Protocol):
    """Provider-neutral contract for discovering canonical security metadata."""

    @property
    def name(self) -> str:
        """Return the normalized provider name."""
        ...

    def discover(
        self,
        symbols: Sequence[str],
    ) -> AssetDiscoveryResult:
        """Return one ordered discovery outcome per normalized input symbol."""
        ...
