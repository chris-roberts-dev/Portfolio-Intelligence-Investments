"""Deterministic in-memory market-data provider for tests and offline workflows.

Development guide references: Sections 9.1 and 19.11.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from types import MappingProxyType
from uuid import UUID

from apps.market_data.providers.base import (
    ProviderBatchResult,
    ProviderIssue,
    ResolvedProviderAsset,
)
from apps.market_data.providers.safety import safe_provider_issue
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.contracts.market_data_validation import (
    MarketDataQualityError,
    validate_price_frame,
)


class MockMarketDataProvider:
    """Deterministic provider backed only by immutable in-memory fixtures."""

    name = "mock"

    def __init__(
        self,
        fixtures: Mapping[UUID, PriceFrame],
        *,
        retrieved_at: datetime,
        issues: Mapping[UUID, ProviderIssue] | None = None,
    ) -> None:
        self._fixtures: Mapping[UUID, PriceFrame] = MappingProxyType(dict(fixtures))
        self._issues: Mapping[UUID, ProviderIssue] = MappingProxyType(
            {
                asset_id: safe_provider_issue(
                    issue.code,
                    issue.message,
                )
                for asset_id, issue in (issues or {}).items()
            }
        )
        self._retrieved_at = retrieved_at

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        """Return deterministic validated bars over inclusive-start/exclusive-end dates."""
        if start >= end:
            raise ValueError("start must be earlier than end")

        frames: dict[UUID, PriceFrame] = {}
        issues: dict[UUID, ProviderIssue] = {}

        for asset in assets:
            configured_issue = self._issues.get(asset.asset_id)

            if configured_issue is not None:
                issues[asset.asset_id] = configured_issue
                continue

            fixture = self._fixtures.get(asset.asset_id)

            if fixture is None:
                issues[asset.asset_id] = safe_provider_issue(
                    "NO_DATA",
                    "No mock fixture is configured for this asset.",
                )
                continue

            try:
                validate_price_frame(fixture)
                self._validate_fixture_provenance(asset, fixture)

                filtered_frame: PriceFrame = tuple(
                    bar for bar in fixture if start <= bar.trade_date < end
                )

                validate_price_frame(filtered_frame)
            except (MarketDataQualityError, ValueError) as exc:
                issues[asset.asset_id] = safe_provider_issue(
                    "DATA_QUALITY_ERROR",
                    str(exc),
                )
                continue

            frames[asset.asset_id] = filtered_frame

        return ProviderBatchResult(
            frames=MappingProxyType(frames),
            issues=MappingProxyType(issues),
            retrieved_at=self._retrieved_at,
        )

    def _validate_fixture_provenance(
        self,
        asset: ResolvedProviderAsset,
        fixture: PriceFrame,
    ) -> None:
        for bar in fixture:
            if bar.asset_id != asset.asset_id:
                raise ValueError(
                    "Mock fixture asset_id does not match the resolved provider asset."
                )

            if bar.source != self.name:
                raise ValueError("Mock fixture source must be 'mock'.")

            if bar.retrieved_at != self._retrieved_at:
                raise ValueError(
                    "Mock fixture retrieved_at must match the batch retrieval timestamp."
                )
