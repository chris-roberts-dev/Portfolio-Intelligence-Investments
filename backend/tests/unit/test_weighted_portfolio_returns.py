"""Unit tests for hypothetical prior-period-weighted portfolio returns."""

from datetime import date
from uuid import UUID

import pytest

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.portfolio.weighted_returns import (
    DatedAssetReturn,
    PortfolioReturnAlignmentError,
    PortfolioWeightError,
    PriorPeriodAssetWeight,
    hypothetical_weighted_portfolio_return,
)

ASSET_A = UUID("00000000-0000-0000-0000-000000000001")
ASSET_B = UUID("00000000-0000-0000-0000-000000000002")
PERIOD_START = date(2025, 1, 2)
PERIOD_END = date(2025, 1, 3)


def asset_return(
    asset_id: UUID,
    value: float,
    *,
    period_start: date = PERIOD_START,
    period_end: date = PERIOD_END,
) -> DatedAssetReturn:
    return DatedAssetReturn(
        asset_id=asset_id,
        period_start=period_start,
        period_end=period_end,
        simple_return=value,
    )


def prior_weight(
    asset_id: UUID,
    value: float,
    *,
    as_of_date: date = PERIOD_START,
) -> PriorPeriodAssetWeight:
    return PriorPeriodAssetWeight(
        asset_id=asset_id,
        as_of_date=as_of_date,
        weight=value,
    )


def test_equal_weight_fixture_uses_prior_period_weights() -> None:
    result = hypothetical_weighted_portfolio_return(
        (
            asset_return(ASSET_A, 0.10),
            asset_return(ASSET_B, -0.05),
        ),
        (
            prior_weight(ASSET_A, 0.50),
            prior_weight(ASSET_B, 0.50),
        ),
    )

    assert result.value == pytest.approx(0.025)
    assert result.period_start == PERIOD_START
    assert result.period_end == PERIOD_END
    assert result.weight_as_of_date == PERIOD_START
    assert result.asset_count == 2
    assert result.weight_sum == pytest.approx(1.0)
    assert result.weight_sum_tolerance == WEIGHT_SUM_TOLERANCE


def test_equal_weight_identical_returns_equal_each_asset_return() -> None:
    identical_return = 0.075

    result = hypothetical_weighted_portfolio_return(
        (
            asset_return(ASSET_A, identical_return),
            asset_return(ASSET_B, identical_return),
        ),
        (
            prior_weight(ASSET_A, 0.50),
            prior_weight(ASSET_B, 0.50),
        ),
    )

    assert result.value == pytest.approx(identical_return)


def test_single_asset_portfolio_return_equals_asset_return() -> None:
    result = hypothetical_weighted_portfolio_return(
        (asset_return(ASSET_A, -0.125),),
        (prior_weight(ASSET_A, 1.0),),
    )

    assert result.value == pytest.approx(-0.125)


def test_same_period_ending_weights_are_rejected() -> None:
    with pytest.raises(
        PortfolioReturnAlignmentError,
        match="as_of_date",
    ):
        hypothetical_weighted_portfolio_return(
            (asset_return(ASSET_A, 0.10),),
            (
                prior_weight(
                    ASSET_A,
                    1.0,
                    as_of_date=PERIOD_END,
                ),
            ),
        )


def test_reordered_weights_are_rejected_instead_of_silently_reordered() -> None:
    with pytest.raises(
        PortfolioReturnAlignmentError,
        match="identical order",
    ):
        hypothetical_weighted_portfolio_return(
            (
                asset_return(ASSET_A, 0.10),
                asset_return(ASSET_B, 0.20),
            ),
            (
                prior_weight(ASSET_B, 0.50),
                prior_weight(ASSET_A, 0.50),
            ),
        )


def test_missing_weight_is_rejected_instead_of_filled() -> None:
    with pytest.raises(
        PortfolioReturnAlignmentError,
        match="equal lengths",
    ):
        hypothetical_weighted_portfolio_return(
            (
                asset_return(ASSET_A, 0.10),
                asset_return(ASSET_B, 0.20),
            ),
            (prior_weight(ASSET_A, 1.0),),
        )


def test_mismatched_return_periods_are_rejected() -> None:
    with pytest.raises(
        PortfolioReturnAlignmentError,
        match="same period_start and period_end",
    ):
        hypothetical_weighted_portfolio_return(
            (
                asset_return(ASSET_A, 0.10),
                asset_return(
                    ASSET_B,
                    0.20,
                    period_end=date(2025, 1, 6),
                ),
            ),
            (
                prior_weight(ASSET_A, 0.50),
                prior_weight(ASSET_B, 0.50),
            ),
        )


def test_materially_invalid_weight_sum_is_rejected() -> None:
    with pytest.raises(
        PortfolioWeightError,
        match="must sum to one",
    ):
        hypothetical_weighted_portfolio_return(
            (
                asset_return(ASSET_A, 0.10),
                asset_return(ASSET_B, 0.20),
            ),
            (
                prior_weight(ASSET_A, 0.40),
                prior_weight(ASSET_B, 0.40),
            ),
        )


def test_weight_sum_within_tolerance_is_not_renormalized() -> None:
    result = hypothetical_weighted_portfolio_return(
        (
            asset_return(ASSET_A, 1.0),
            asset_return(ASSET_B, 1.0),
        ),
        (
            prior_weight(ASSET_A, 0.60),
            prior_weight(ASSET_B, 0.399999995),
        ),
    )

    assert result.weight_sum == pytest.approx(0.999999995)
    assert result.value == pytest.approx(0.999999995)


def test_invalid_simple_return_and_weight_values_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="greater than or equal to -1",
    ):
        asset_return(ASSET_A, -1.01)

    with pytest.raises(ValueError, match="finite"):
        asset_return(ASSET_A, float("nan"))

    with pytest.raises(ValueError, match="negative"):
        prior_weight(ASSET_A, -0.01)
