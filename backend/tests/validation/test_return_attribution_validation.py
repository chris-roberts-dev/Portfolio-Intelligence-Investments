from datetime import date
from uuid import UUID

import pytest

from portfolio_engine.portfolio.return_attribution import (
    AssetPeriodValueChange,
    attribute_daily_portfolio_return,
    link_daily_return_attributions,
)

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")


def test_independent_trade_and_linking_fixture_matches_manual_attribution() -> None:
    first = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=100.0,
        portfolio_return=0.04,
        assets=(
            AssetPeriodValueChange(
                asset_id=A,
                starting_market_value=100.0,
                ending_market_value=55.0,
                internal_cash_flow=50.0,
            ),
            AssetPeriodValueChange(
                asset_id=B,
                starting_market_value=0.0,
                ending_market_value=50.0,
                internal_cash_flow=-51.0,
            ),
        ),
    )
    second = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 5),
        period_end=date(2026, 1, 6),
        prior_portfolio_value=104.0,
        portfolio_return=4.0 / 104.0,
        assets=(
            AssetPeriodValueChange(
                A,
                55.0,
                57.0,
            ),
            AssetPeriodValueChange(
                B,
                50.0,
                52.0,
            ),
        ),
    )

    result = link_daily_return_attributions(
        (
            first,
            second,
        )
    )

    # Day 1:
    # A = (55 - 100 + 50) / 100 = +5%.
    # B = (50 - 0 - 51) / 100 = -1%.
    # Portfolio = +4%.
    #
    # Day 2:
    # Both assets earn 2 / 104.
    # Wealth linking scales day-2 contribution by 1.04,
    # so each adds exactly +2 percentage points.
    assert result.asset_contributions[0].contribution == pytest.approx(0.07)
    assert result.asset_contributions[1].contribution == pytest.approx(0.01)
    assert result.cumulative_return == pytest.approx(0.08)
    assert result.asset_contribution_total == pytest.approx(0.08)
    assert result.unattributed_contribution == pytest.approx(0.0)
    assert result.reconciliation_error == pytest.approx(0.0)
