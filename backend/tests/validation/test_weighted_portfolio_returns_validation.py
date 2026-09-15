"""Independent validation fixtures for hypothetical weighted returns."""

from datetime import date
from uuid import UUID

import pytest

from portfolio_engine.portfolio.weighted_returns import (
    DatedAssetReturn,
    PriorPeriodAssetWeight,
    hypothetical_weighted_portfolio_return,
)


def test_known_two_asset_weighted_return_matches_manual_calculation() -> None:
    period_start = date(2025, 1, 2)
    period_end = date(2025, 1, 3)
    asset_a = UUID("00000000-0000-0000-0000-000000000001")
    asset_b = UUID("00000000-0000-0000-0000-000000000002")

    result = hypothetical_weighted_portfolio_return(
        (
            DatedAssetReturn(
                asset_id=asset_a,
                period_start=period_start,
                period_end=period_end,
                simple_return=0.10,
            ),
            DatedAssetReturn(
                asset_id=asset_b,
                period_start=period_start,
                period_end=period_end,
                simple_return=-0.05,
            ),
        ),
        (
            PriorPeriodAssetWeight(
                asset_id=asset_a,
                as_of_date=period_start,
                weight=0.60,
            ),
            PriorPeriodAssetWeight(
                asset_id=asset_b,
                as_of_date=period_start,
                weight=0.40,
            ),
        ),
    )

    expected = 0.60 * 0.10 + 0.40 * -0.05

    assert expected == pytest.approx(0.04)
    assert result.value == pytest.approx(expected)
