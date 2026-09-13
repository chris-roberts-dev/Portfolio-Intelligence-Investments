"""Reusable deterministic contract assertions for market-data providers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from uuid import UUID

from apps.market_data.providers.base import (
    MarketDataProvider,
    ProviderIssue,
    ResolvedProviderAsset,
)
from portfolio_engine.contracts.market_data import PriceBar, PriceFrame
from portfolio_engine.contracts.market_data_validation import validate_price_frame

type ProviderFactoryUnderTest = Callable[
    [Mapping[UUID, PriceFrame], Mapping[UUID, ProviderIssue], datetime],
    MarketDataProvider,
]

ASSET_A_ID = UUID("00000000-0000-0000-0000-000000000001")
ASSET_B_ID = UUID("00000000-0000-0000-0000-000000000002")
RETRIEVED_AT = datetime(2026, 1, 5, 12, tzinfo=UTC)

ASSET_A = ResolvedProviderAsset(
    asset_id=ASSET_A_ID,
    canonical_symbol="AAA",
    provider_symbol="AAA",
)
ASSET_B = ResolvedProviderAsset(
    asset_id=ASSET_B_ID,
    canonical_symbol="BBB",
    provider_symbol="BBB",
)


class MarketDataProviderContract:
    """Reusable deterministic assertions shared by provider implementations."""

    def __init__(
        self,
        factory: ProviderFactoryUnderTest,
        *,
        provider_name: str,
    ) -> None:
        self._factory = factory
        self._provider_name = provider_name

    def assert_multi_asset_association(self) -> None:
        fixtures = {
            ASSET_A_ID: self._make_frame(
                ASSET_A_ID,
                (date(2026, 1, 2), date(2026, 1, 3)),
            ),
            ASSET_B_ID: self._make_frame(
                ASSET_B_ID,
                (date(2026, 1, 2), date(2026, 1, 3)),
            ),
        }
        provider = self._factory(fixtures, {}, RETRIEVED_AT)

        result = provider.get_daily_bars(
            (ASSET_A, ASSET_B),
            date(2026, 1, 1),
            date(2026, 1, 4),
        )

        assert tuple(result.frames) == (ASSET_A_ID, ASSET_B_ID)
        assert all(bar.asset_id == ASSET_A_ID for bar in result.frames[ASSET_A_ID])
        assert all(bar.asset_id == ASSET_B_ID for bar in result.frames[ASSET_B_ID])
        assert result.issues == {}

    def assert_returned_bars_are_valid(self) -> None:
        fixtures = {
            ASSET_A_ID: self._make_frame(
                ASSET_A_ID,
                (
                    date(2026, 1, 2),
                    date(2026, 1, 3),
                    date(2026, 1, 4),
                ),
            )
        }
        provider = self._factory(fixtures, {}, RETRIEVED_AT)

        result = provider.get_daily_bars(
            (ASSET_A,),
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        frame = result.frames[ASSET_A_ID]

        assert validate_price_frame(frame) is frame
        assert tuple(bar.trade_date for bar in frame) == (
            date(2026, 1, 2),
            date(2026, 1, 3),
            date(2026, 1, 4),
        )

    def assert_inclusive_start_exclusive_end(self) -> None:
        fixtures = {
            ASSET_A_ID: self._make_frame(
                ASSET_A_ID,
                (
                    date(2026, 1, 1),
                    date(2026, 1, 2),
                    date(2026, 1, 3),
                ),
            )
        }
        provider = self._factory(fixtures, {}, RETRIEVED_AT)

        result = provider.get_daily_bars(
            (ASSET_A,),
            date(2026, 1, 2),
            date(2026, 1, 3),
        )

        assert tuple(bar.trade_date for bar in result.frames[ASSET_A_ID]) == (date(2026, 1, 2),)

    def assert_empty_fixture_remains_empty(
        self,
        *,
        expected_issue_code: str | None = None,
    ) -> None:
        provider = self._factory(
            {ASSET_A_ID: ()},
            {},
            RETRIEVED_AT,
        )

        result = provider.get_daily_bars(
            (ASSET_A,),
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        if expected_issue_code is None:
            assert result.frames[ASSET_A_ID] == ()
            assert result.issues == {}
        else:
            assert ASSET_A_ID not in result.frames
            assert result.issues[ASSET_A_ID].code == expected_issue_code

    def assert_configured_no_data_issue(self) -> None:
        provider = self._factory(
            {},
            {
                ASSET_A_ID: ProviderIssue(
                    code="NO_DATA",
                    message="Configured deterministic no-data response.",
                )
            },
            RETRIEVED_AT,
        )

        result = provider.get_daily_bars(
            (ASSET_A,),
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        assert ASSET_A_ID not in result.frames
        assert result.issues[ASSET_A_ID].code == "NO_DATA"

    def assert_partial_failure_preserves_success(
        self,
        *,
        expected_issue_code: str = "FAILED",
    ) -> None:
        provider = self._factory(
            {
                ASSET_A_ID: self._make_frame(
                    ASSET_A_ID,
                    (date(2026, 1, 2),),
                )
            },
            {
                ASSET_B_ID: ProviderIssue(
                    code="FAILED",
                    message="Configured deterministic provider failure.",
                )
            },
            RETRIEVED_AT,
        )

        result = provider.get_daily_bars(
            (ASSET_A, ASSET_B),
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        assert tuple(result.frames) == (ASSET_A_ID,)
        assert result.issues[ASSET_B_ID].code == expected_issue_code

    def assert_batch_provenance(self) -> None:
        provider = self._factory(
            {
                ASSET_A_ID: self._make_frame(
                    ASSET_A_ID,
                    (date(2026, 1, 2),),
                )
            },
            {},
            RETRIEVED_AT,
        )

        result = provider.get_daily_bars(
            (ASSET_A,),
            date(2026, 1, 1),
            date(2026, 1, 5),
        )

        assert provider.name == self._provider_name
        assert result.retrieved_at == RETRIEVED_AT
        assert all(
            bar.source == self._provider_name and bar.retrieved_at == RETRIEVED_AT
            for bar in result.frames[ASSET_A_ID]
        )

    def _make_frame(
        self,
        asset_id: UUID,
        trade_dates: tuple[date, ...],
    ) -> PriceFrame:
        return tuple(
            PriceBar(
                asset_id=asset_id,
                trade_date=trade_date,
                open=100.0,
                high=103.0,
                low=99.0,
                close=102.0,
                adjusted_close=101.5,
                volume=1_000_000,
                source=self._provider_name,
                retrieved_at=RETRIEVED_AT,
            )
            for trade_date in trade_dates
        )
