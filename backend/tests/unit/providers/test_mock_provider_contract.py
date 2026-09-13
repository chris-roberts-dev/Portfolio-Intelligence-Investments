"""Shared provider-contract tests exercised against the mock provider."""

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from apps.market_data.providers.base import ProviderIssue
from apps.market_data.providers.mock import MockMarketDataProvider
from portfolio_engine.contracts.market_data import PriceFrame
from tests.unit.providers.provider_contract import MarketDataProviderContract


def make_mock_provider(
    fixtures: Mapping[UUID, PriceFrame],
    issues: Mapping[UUID, ProviderIssue],
    retrieved_at: datetime,
) -> MockMarketDataProvider:
    """Build the mock implementation for the reusable provider contract."""
    return MockMarketDataProvider(
        fixtures,
        issues=issues,
        retrieved_at=retrieved_at,
    )


CONTRACT = MarketDataProviderContract(
    make_mock_provider,
    provider_name="mock",
)


def test_mock_provider_preserves_multi_asset_association() -> None:
    CONTRACT.assert_multi_asset_association()


def test_mock_provider_returns_valid_ordered_unique_bars() -> None:
    CONTRACT.assert_returned_bars_are_valid()


def test_mock_provider_honors_inclusive_start_exclusive_end() -> None:
    CONTRACT.assert_inclusive_start_exclusive_end()


def test_mock_provider_preserves_empty_results() -> None:
    CONTRACT.assert_empty_fixture_remains_empty()


def test_mock_provider_supports_configured_no_data_issue() -> None:
    CONTRACT.assert_configured_no_data_issue()


def test_mock_provider_preserves_success_during_partial_failure() -> None:
    CONTRACT.assert_partial_failure_preserves_success()


def test_mock_provider_retains_batch_provenance() -> None:
    CONTRACT.assert_batch_provenance()
