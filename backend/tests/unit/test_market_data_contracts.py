"""Unit tests for canonical market-data contracts."""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import uuid4

from apps.market_data.providers.base import (
    MarketDataProvider,
    ProviderBatchResult,
    ProviderIssue,
    ResolvedProviderAsset,
)
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame


class StubProvider:
    """Deterministic structural implementation used only for contract testing."""

    @property
    def name(self) -> str:
        return "stub"

    def get_daily_bars(
        self,
        assets: Sequence[ResolvedProviderAsset],
        start: date,
        end: date,
    ) -> ProviderBatchResult:
        del start, end
        return ProviderBatchResult(
            frames={asset.asset_id: () for asset in assets},
            issues={},
            retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
        )


def test_price_frame_preserves_internal_asset_identity_and_daily_fields() -> None:
    asset_id = uuid4()
    retrieved_at = datetime(2026, 1, 3, 12, tzinfo=UTC)
    bar = PriceBar(
        asset_id=asset_id,
        trade_date=date(2026, 1, 2),
        open=100.0,
        high=103.0,
        low=99.0,
        close=102.0,
        adjusted_close=101.5,
        volume=1_000_000,
        source="stub",
        retrieved_at=retrieved_at,
    )
    frame: PriceFrame = (bar,)

    assert frame[0].asset_id == asset_id
    assert frame[0].trade_date == date(2026, 1, 2)
    assert frame[0].adjusted_close == 101.5
    assert frame[0].source == "stub"
    assert frame[0].retrieved_at == retrieved_at


def test_provider_batch_result_is_keyed_by_internal_asset_id() -> None:
    asset_id = uuid4()
    result = ProviderBatchResult(
        frames={asset_id: ()},
        issues={
            asset_id: ProviderIssue(
                code="NO_DATA",
                message="No bars were returned for the requested period.",
            )
        },
        retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert tuple(result.frames) == (asset_id,)
    assert result.issues[asset_id].code == "NO_DATA"


def test_market_data_provider_supports_structural_implementations() -> None:
    provider: MarketDataProvider = StubProvider()

    assert isinstance(provider, MarketDataProvider)
    assert provider.name == "stub"
