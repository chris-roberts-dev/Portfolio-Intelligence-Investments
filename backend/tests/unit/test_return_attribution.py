from datetime import date
from uuid import UUID

import pytest

from portfolio_engine.portfolio.return_attribution import (
    AssetPeriodValueChange,
    ReturnAttributionError,
    attribute_daily_portfolio_return,
    link_daily_return_attributions,
)

A = UUID("00000000-0000-0000-0000-000000000001")
B = UUID("00000000-0000-0000-0000-000000000002")


def test_daily_attribution_reconciles_simple_two_asset_period() -> None:
    result = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=100.0,
        portfolio_return=0.04,
        assets=(
            AssetPeriodValueChange(
                asset_id=A,
                starting_market_value=60.0,
                ending_market_value=66.0,
            ),
            AssetPeriodValueChange(
                asset_id=B,
                starting_market_value=40.0,
                ending_market_value=38.0,
            ),
        ),
    )

    assert tuple(item.contribution for item in result.asset_contributions) == pytest.approx(
        (
            0.06,
            -0.02,
        )
    )
    assert result.asset_contribution_total == pytest.approx(0.04)
    assert result.unattributed_contribution == pytest.approx(0.0)
    assert result.reconciliation_error == pytest.approx(0.0)


def test_internal_trade_cash_flows_attribute_execution_effect_and_fees() -> None:
    result = attribute_daily_portfolio_return(
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

    assert result.asset_contributions[0].profit_loss == pytest.approx(5.0)
    assert result.asset_contributions[0].contribution == pytest.approx(0.05)
    assert result.asset_contributions[1].profit_loss == pytest.approx(-1.0)
    assert result.asset_contributions[1].contribution == pytest.approx(-0.01)
    assert result.unattributed_contribution == pytest.approx(0.0)


def test_dividend_cash_is_attributed_to_its_asset() -> None:
    result = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=100.0,
        portfolio_return=0.05,
        assets=(
            AssetPeriodValueChange(
                asset_id=A,
                starting_market_value=100.0,
                ending_market_value=100.0,
                internal_cash_flow=5.0,
            ),
        ),
    )

    assert result.asset_contributions[0].profit_loss == pytest.approx(5.0)
    assert result.asset_contributions[0].contribution == pytest.approx(0.05)
    assert result.unattributed_contribution == pytest.approx(0.0)


def test_unexplained_difference_remains_explicit_residual() -> None:
    result = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=100.0,
        portfolio_return=0.05,
        assets=(
            AssetPeriodValueChange(
                asset_id=A,
                starting_market_value=100.0,
                ending_market_value=104.0,
            ),
        ),
    )

    assert result.asset_contribution_total == pytest.approx(0.04)
    assert result.unattributed_contribution == pytest.approx(0.01)
    assert (result.asset_contribution_total + result.unattributed_contribution) == pytest.approx(
        result.portfolio_return
    )


def test_wealth_linking_reconciles_to_chain_linked_twr() -> None:
    first = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=100.0,
        portfolio_return=0.04,
        assets=(
            AssetPeriodValueChange(
                A,
                100.0,
                55.0,
                50.0,
            ),
            AssetPeriodValueChange(
                B,
                0.0,
                50.0,
                -51.0,
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

    assert result.cumulative_return == pytest.approx(0.08)
    assert tuple(item.contribution for item in result.asset_contributions) == pytest.approx(
        (
            0.07,
            0.01,
        )
    )
    assert result.asset_contribution_total == pytest.approx(0.08)
    assert result.unattributed_contribution == pytest.approx(0.0)
    assert result.reconciliation_error == pytest.approx(0.0)


def test_invalid_period_prior_value_and_duplicate_assets_are_rejected() -> None:
    with pytest.raises(
        ReturnAttributionError,
        match="period_start",
    ):
        attribute_daily_portfolio_return(
            period_start=date(2026, 1, 5),
            period_end=date(2026, 1, 5),
            prior_portfolio_value=100.0,
            portfolio_return=0.0,
            assets=(),
        )

    with pytest.raises(
        ReturnAttributionError,
        match="prior_portfolio_value",
    ):
        attribute_daily_portfolio_return(
            period_start=date(2026, 1, 2),
            period_end=date(2026, 1, 5),
            prior_portfolio_value=0.0,
            portfolio_return=0.0,
            assets=(),
        )

    duplicated = AssetPeriodValueChange(
        A,
        10.0,
        10.0,
    )

    with pytest.raises(
        ReturnAttributionError,
        match="duplicate asset IDs",
    ):
        attribute_daily_portfolio_return(
            period_start=date(2026, 1, 2),
            period_end=date(2026, 1, 5),
            prior_portfolio_value=100.0,
            portfolio_return=0.0,
            assets=(
                duplicated,
                duplicated,
            ),
        )


def test_linking_requires_contiguous_period_boundaries() -> None:
    first = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=100.0,
        portfolio_return=0.0,
        assets=(),
    )
    second = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 6),
        period_end=date(2026, 1, 7),
        prior_portfolio_value=100.0,
        portfolio_return=0.0,
        assets=(),
    )

    with pytest.raises(
        ReturnAttributionError,
        match="contiguous",
    ):
        link_daily_return_attributions(
            (
                first,
                second,
            )
        )
