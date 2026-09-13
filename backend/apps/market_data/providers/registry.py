"""Settings-independent market-data provider registry.

Development guide references: Sections 4.4, 9.1, and 9.5.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from apps.market_data.providers.base import MarketDataProvider

type ProviderFactory = Callable[[], MarketDataProvider]


class ProviderRegistryErrorCode(StrEnum):
    """Stable failure codes for provider registration and resolution."""

    BLANK_NAME = "BLANK_NAME"
    DUPLICATE_PROVIDER = "DUPLICATE_PROVIDER"
    UNKNOWN_PROVIDER = "UNKNOWN_PROVIDER"
    PROVIDER_NAME_MISMATCH = "PROVIDER_NAME_MISMATCH"


class ProviderRegistryError(ValueError):
    """Raised when provider registration or resolution violates registry rules."""

    def __init__(
        self,
        code: ProviderRegistryErrorCode,
        message: str,
        *,
        provider_name: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider_name = provider_name


class MarketDataProviderRegistry:
    """Explicit provider factory registry with no automatic fallback."""

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered provider names in registration order."""
        return tuple(self._factories)

    def register(
        self,
        name: str,
        factory: ProviderFactory,
    ) -> None:
        """Register one provider factory under a stable lowercase name."""
        normalized_name = _normalize_provider_name(name)

        if normalized_name in self._factories:
            raise ProviderRegistryError(
                ProviderRegistryErrorCode.DUPLICATE_PROVIDER,
                f"Provider {normalized_name!r} is already registered.",
                provider_name=normalized_name,
            )

        self._factories[normalized_name] = factory

    def create(self, name: str) -> MarketDataProvider:
        """Create exactly the requested provider without fallback."""
        normalized_name = _normalize_provider_name(name)

        try:
            factory = self._factories[normalized_name]
        except KeyError as exc:
            raise ProviderRegistryError(
                ProviderRegistryErrorCode.UNKNOWN_PROVIDER,
                f"Provider {normalized_name!r} is not registered.",
                provider_name=normalized_name,
            ) from exc

        provider = factory()
        actual_name = _normalize_provider_name(provider.name)

        if actual_name != normalized_name:
            raise ProviderRegistryError(
                ProviderRegistryErrorCode.PROVIDER_NAME_MISMATCH,
                (
                    f"Provider factory registered as {normalized_name!r} "
                    f"returned provider named {actual_name!r}."
                ),
                provider_name=normalized_name,
            )

        return provider


def _normalize_provider_name(name: str) -> str:
    normalized_name = name.strip().lower()

    if not normalized_name:
        raise ProviderRegistryError(
            ProviderRegistryErrorCode.BLANK_NAME,
            "Provider name must not be blank.",
            provider_name=normalized_name,
        )

    return normalized_name
