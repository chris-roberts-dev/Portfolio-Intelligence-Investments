"""Django-backed market-data provider configuration.

Development guide references: Sections 4.4, 9.1, and 9.5.
Amendment reference: docs/amendments/0001-phase-2-mock-provider-default.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType

from django.conf import settings

from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.providers.registry import (
    MarketDataProviderRegistry,
    ProviderFactory,
)
from apps.market_data.providers.yfinance import YFinanceMarketDataProvider

MOCK_PROVIDER_RETRIEVED_AT = datetime(2000, 1, 1, tzinfo=UTC)


def _build_configured_mock_provider() -> MockMarketDataProvider:
    """Build the deterministic empty mock used by configured provider resolution."""
    return MockMarketDataProvider(
        {},
        retrieved_at=MOCK_PROVIDER_RETRIEVED_AT,
    )


def _build_configured_yfinance_provider() -> YFinanceMarketDataProvider:
    """Build the configured yfinance adapter without performing provider I/O."""
    return YFinanceMarketDataProvider()


REGISTERED_PROVIDER_FACTORIES: Mapping[str, ProviderFactory] = MappingProxyType(
    {
        "mock": _build_configured_mock_provider,
        "yfinance": _build_configured_yfinance_provider,
    }
)


class ProviderConfigurationErrorCode(StrEnum):
    """Stable failure codes for server-side provider configuration."""

    BLANK_DEFAULT_PROVIDER = "BLANK_DEFAULT_PROVIDER"
    EMPTY_ALLOWED_PROVIDERS = "EMPTY_ALLOWED_PROVIDERS"
    BLANK_ALLOWED_PROVIDER = "BLANK_ALLOWED_PROVIDER"
    DEFAULT_PROVIDER_UNREGISTERED = "DEFAULT_PROVIDER_UNREGISTERED"
    ALLOWED_PROVIDER_UNREGISTERED = "ALLOWED_PROVIDER_UNREGISTERED"
    DEFAULT_PROVIDER_NOT_ALLOWED = "DEFAULT_PROVIDER_NOT_ALLOWED"
    BLANK_REQUESTED_PROVIDER = "BLANK_REQUESTED_PROVIDER"
    PROVIDER_NOT_ALLOWED = "PROVIDER_NOT_ALLOWED"


class ProviderConfigurationError(ValueError):
    """Raised when configured market-data provider selection is invalid."""

    def __init__(
        self,
        code: ProviderConfigurationErrorCode,
        message: str,
        *,
        provider_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider_name = provider_name


@dataclass(frozen=True, slots=True)
class MarketDataProviderConfiguration:
    """Validated default-provider and allowlist configuration."""

    default_provider: str
    allowed_providers: tuple[str, ...]


def load_market_data_provider_configuration(
    *,
    default_provider: str | None = None,
    allowed_providers: Sequence[str] | None = None,
    provider_factories: Mapping[str, ProviderFactory] = REGISTERED_PROVIDER_FACTORIES,
) -> MarketDataProviderConfiguration:
    """Load and validate provider configuration against registered factories."""
    configured_default = (
        settings.MARKET_DATA_DEFAULT_PROVIDER if default_provider is None else default_provider
    )
    configured_allowed = (
        settings.MARKET_DATA_ALLOWED_PROVIDERS if allowed_providers is None else allowed_providers
    )

    normalized_default = configured_default.strip().lower()

    if not normalized_default:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.BLANK_DEFAULT_PROVIDER,
            "MARKET_DATA_DEFAULT_PROVIDER must not be blank.",
            provider_name=normalized_default,
        )

    normalized_allowed: list[str] = []
    seen_allowed: set[str] = set()

    for configured_name in configured_allowed:
        normalized_name = configured_name.strip().lower()

        if not normalized_name:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.BLANK_ALLOWED_PROVIDER,
                "MARKET_DATA_ALLOWED_PROVIDERS must not contain blank names.",
                provider_name=normalized_name,
            )

        if normalized_name not in seen_allowed:
            seen_allowed.add(normalized_name)
            normalized_allowed.append(normalized_name)

    if not normalized_allowed:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.EMPTY_ALLOWED_PROVIDERS,
            "MARKET_DATA_ALLOWED_PROVIDERS must contain at least one provider.",
        )

    if normalized_default not in provider_factories:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.DEFAULT_PROVIDER_UNREGISTERED,
            f"Default provider {normalized_default!r} is not registered.",
            provider_name=normalized_default,
        )

    for allowed_name in normalized_allowed:
        if allowed_name not in provider_factories:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.ALLOWED_PROVIDER_UNREGISTERED,
                f"Allowed provider {allowed_name!r} is not registered.",
                provider_name=allowed_name,
            )

    if normalized_default not in seen_allowed:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.DEFAULT_PROVIDER_NOT_ALLOWED,
            f"Default provider {normalized_default!r} is not in the allowlist.",
            provider_name=normalized_default,
        )

    return MarketDataProviderConfiguration(
        default_provider=normalized_default,
        allowed_providers=tuple(normalized_allowed),
    )


def build_configured_provider_registry(
    *,
    configuration: MarketDataProviderConfiguration | None = None,
    provider_factories: Mapping[str, ProviderFactory] = REGISTERED_PROVIDER_FACTORIES,
) -> tuple[MarketDataProviderConfiguration, MarketDataProviderRegistry]:
    """Build an explicit registry containing only configured allowed providers."""
    resolved_configuration = configuration or load_market_data_provider_configuration(
        provider_factories=provider_factories
    )

    registered_names = set(provider_factories)

    if resolved_configuration.default_provider not in registered_names:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.DEFAULT_PROVIDER_UNREGISTERED,
            (f"Default provider {resolved_configuration.default_provider!r} is not registered."),
            provider_name=resolved_configuration.default_provider,
        )

    registry = MarketDataProviderRegistry()

    for provider_name in resolved_configuration.allowed_providers:
        try:
            factory = provider_factories[provider_name]
        except KeyError as exc:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.ALLOWED_PROVIDER_UNREGISTERED,
                f"Allowed provider {provider_name!r} is not registered.",
                provider_name=provider_name,
            ) from exc

        registry.register(provider_name, factory)

    return resolved_configuration, registry


def resolve_market_data_provider(
    requested_provider: str | None = None,
    *,
    configuration: MarketDataProviderConfiguration | None = None,
    provider_factories: Mapping[str, ProviderFactory] = REGISTERED_PROVIDER_FACTORIES,
) -> MarketDataProvider:
    """Resolve exactly one configured provider without cross-provider fallback."""
    resolved_configuration, registry = build_configured_provider_registry(
        configuration=configuration,
        provider_factories=provider_factories,
    )

    if requested_provider is None:
        provider_name = resolved_configuration.default_provider
    else:
        provider_name = requested_provider.strip().lower()

        if not provider_name:
            raise ProviderConfigurationError(
                ProviderConfigurationErrorCode.BLANK_REQUESTED_PROVIDER,
                "Requested provider must not be blank.",
                provider_name=provider_name,
            )

    if provider_name not in resolved_configuration.allowed_providers:
        raise ProviderConfigurationError(
            ProviderConfigurationErrorCode.PROVIDER_NOT_ALLOWED,
            f"Provider {provider_name!r} is not allowed.",
            provider_name=provider_name,
        )

    return registry.create(provider_name)
