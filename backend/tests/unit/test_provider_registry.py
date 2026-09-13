"""Unit tests for the settings-independent provider registry."""

from datetime import UTC, datetime

import pytest

from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.providers.registry import (
    MarketDataProviderRegistry,
    ProviderRegistryError,
    ProviderRegistryErrorCode,
)

RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)


def make_mock_provider() -> MockMarketDataProvider:
    """Return an empty deterministic mock provider."""
    return MockMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
    )


def test_registry_normalizes_provider_name_and_creates_requested_provider() -> None:
    registry = MarketDataProviderRegistry()
    registry.register(" Mock ", make_mock_provider)

    provider = registry.create("MOCK")

    assert registry.names == ("mock",)
    assert provider.name == "mock"


def test_registry_rejects_blank_provider_name() -> None:
    registry = MarketDataProviderRegistry()

    with pytest.raises(ProviderRegistryError) as exc_info:
        registry.register("  ", make_mock_provider)

    assert exc_info.value.code is ProviderRegistryErrorCode.BLANK_NAME


def test_registry_rejects_case_insensitive_duplicate_registration() -> None:
    registry = MarketDataProviderRegistry()
    registry.register("mock", make_mock_provider)

    with pytest.raises(ProviderRegistryError) as exc_info:
        registry.register("MOCK", make_mock_provider)

    assert exc_info.value.code is ProviderRegistryErrorCode.DUPLICATE_PROVIDER


def test_registry_rejects_unknown_provider_without_fallback() -> None:
    registry = MarketDataProviderRegistry()
    registry.register("mock", make_mock_provider)

    with pytest.raises(ProviderRegistryError) as exc_info:
        registry.create("other")

    assert exc_info.value.code is ProviderRegistryErrorCode.UNKNOWN_PROVIDER
    assert exc_info.value.provider_name == "other"


def test_registry_rejects_factory_name_mismatch() -> None:
    class WrongNameProvider(MockMarketDataProvider):
        name = "other"

    def make_wrong_provider() -> WrongNameProvider:
        return WrongNameProvider(
            {},
            retrieved_at=RETRIEVED_AT,
        )

    registry = MarketDataProviderRegistry()
    registry.register("mock", make_wrong_provider)

    with pytest.raises(ProviderRegistryError) as exc_info:
        registry.create("mock")

    assert exc_info.value.code is ProviderRegistryErrorCode.PROVIDER_NAME_MISMATCH
