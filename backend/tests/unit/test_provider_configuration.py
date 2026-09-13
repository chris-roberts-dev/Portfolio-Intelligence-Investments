"""Unit tests for Django-backed market-data provider configuration."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from apps.market_data.providers.base import MarketDataProvider
from apps.market_data.providers.configuration import (
    MarketDataProviderConfiguration,
    ProviderConfigurationError,
    ProviderConfigurationErrorCode,
    load_market_data_provider_configuration,
    resolve_market_data_provider,
)
from apps.market_data.providers.mock import MockMarketDataProvider
from apps.market_data.providers.registry import ProviderFactory
from apps.market_data.providers.yfinance import YFinanceMarketDataProvider
from config.settings import dev as dev_settings
from config.settings import test as test_settings

RETRIEVED_AT = datetime(2000, 1, 1, tzinfo=UTC)


class OtherMockProvider(MockMarketDataProvider):
    """Registered test provider used only to prove allowlist enforcement."""

    name = "other"


def make_mock_provider() -> MockMarketDataProvider:
    """Return a deterministic configured mock provider."""
    return MockMarketDataProvider(
        {},
        retrieved_at=RETRIEVED_AT,
    )


def make_other_provider() -> OtherMockProvider:
    """Return a second registered provider for allowlist-boundary tests."""
    return OtherMockProvider(
        {},
        retrieved_at=RETRIEVED_AT,
    )


REGISTERED_TEST_FACTORIES: Mapping[str, ProviderFactory] = MappingProxyType(
    {
        "mock": make_mock_provider,
        "other": make_other_provider,
    }
)


def test_development_settings_resolve_yfinance_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.delenv("MARKET_DATA_DEFAULT_PROVIDER", raising=False)
        patch.delenv("MARKET_DATA_ALLOWED_PROVIDERS", raising=False)
        settings_module = importlib.reload(dev_settings)

        configuration = load_market_data_provider_configuration(
            default_provider=settings_module.MARKET_DATA_DEFAULT_PROVIDER,
            allowed_providers=settings_module.MARKET_DATA_ALLOWED_PROVIDERS,
        )
        provider = resolve_market_data_provider(configuration=configuration)

        assert configuration.default_provider == "yfinance"
        assert configuration.allowed_providers == ("yfinance", "mock")
        assert isinstance(provider, YFinanceMarketDataProvider)
        assert provider.name == "yfinance"

    importlib.reload(dev_settings)


def test_test_settings_resolve_deterministic_mock_provider() -> None:
    configuration = load_market_data_provider_configuration(
        default_provider=test_settings.MARKET_DATA_DEFAULT_PROVIDER,
        allowed_providers=test_settings.MARKET_DATA_ALLOWED_PROVIDERS,
    )

    provider = resolve_market_data_provider(configuration=configuration)

    assert configuration.default_provider == "mock"
    assert configuration.allowed_providers == ("mock",)
    assert isinstance(provider, MockMarketDataProvider)
    assert provider.name == "mock"


def test_blank_default_provider_fails() -> None:
    with pytest.raises(ProviderConfigurationError) as exc_info:
        load_market_data_provider_configuration(
            default_provider="  ",
            allowed_providers=("mock",),
        )

    assert exc_info.value.code is ProviderConfigurationErrorCode.BLANK_DEFAULT_PROVIDER


def test_unknown_default_provider_fails() -> None:
    with pytest.raises(ProviderConfigurationError) as exc_info:
        load_market_data_provider_configuration(
            default_provider="alpaca",
            allowed_providers=("alpaca",),
        )

    assert exc_info.value.code is ProviderConfigurationErrorCode.DEFAULT_PROVIDER_UNREGISTERED
    assert exc_info.value.provider_name == "alpaca"


def test_unregistered_provider_cannot_be_enabled_by_configuration() -> None:
    with pytest.raises(ProviderConfigurationError) as exc_info:
        load_market_data_provider_configuration(
            default_provider="yfinance",
            allowed_providers=("yfinance", "alpaca"),
        )

    assert exc_info.value.code is ProviderConfigurationErrorCode.ALLOWED_PROVIDER_UNREGISTERED
    assert exc_info.value.provider_name == "alpaca"


def test_default_provider_must_be_in_allowlist() -> None:
    with pytest.raises(ProviderConfigurationError) as exc_info:
        load_market_data_provider_configuration(
            default_provider="mock",
            allowed_providers=("other",),
            provider_factories=REGISTERED_TEST_FACTORIES,
        )

    assert exc_info.value.code is ProviderConfigurationErrorCode.DEFAULT_PROVIDER_NOT_ALLOWED


def test_requested_registered_provider_cannot_bypass_allowlist() -> None:
    configuration = MarketDataProviderConfiguration(
        default_provider="mock",
        allowed_providers=("mock",),
    )

    with pytest.raises(ProviderConfigurationError) as exc_info:
        resolve_market_data_provider(
            "yfinance",
            configuration=configuration,
        )

    assert exc_info.value.code is ProviderConfigurationErrorCode.PROVIDER_NOT_ALLOWED
    assert exc_info.value.provider_name == "yfinance"


def test_provider_factory_failure_does_not_fallback_to_default() -> None:
    calls: list[str] = []

    def make_failing_provider() -> MarketDataProvider:
        calls.append("yfinance")
        raise RuntimeError("configured provider construction failure")

    def make_fallback_provider() -> MockMarketDataProvider:
        calls.append("mock")
        return make_mock_provider()

    provider_factories: Mapping[str, ProviderFactory] = MappingProxyType(
        {
            "mock": make_fallback_provider,
            "yfinance": make_failing_provider,
        }
    )
    configuration = MarketDataProviderConfiguration(
        default_provider="mock",
        allowed_providers=("yfinance", "mock"),
    )

    with pytest.raises(RuntimeError, match="configured provider construction failure"):
        resolve_market_data_provider(
            "yfinance",
            configuration=configuration,
            provider_factories=provider_factories,
        )

    assert calls == ["yfinance"]


def test_allowed_provider_names_are_normalized_and_deduplicated() -> None:
    configuration = load_market_data_provider_configuration(
        default_provider=" MOCK ",
        allowed_providers=("mock", " MOCK "),
    )

    assert configuration.default_provider == "mock"
    assert configuration.allowed_providers == ("mock",)
