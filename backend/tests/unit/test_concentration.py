"""Unit tests for canonical portfolio concentration metrics."""

import pytest

from portfolio_engine.config import WEIGHT_SUM_TOLERANCE
from portfolio_engine.risk.concentration import (
    NormalizedPortfolioWeights,
    portfolio_concentration,
)


def test_single_security_portfolio_has_maximum_concentration() -> None:
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=(1.0,),
        )
    )

    assert result.largest_position_weight == 1.0
    assert result.herfindahl_hirschman_index == 1.0
    assert result.security_position_count == 1
    assert result.cash_weight == 0.0
    assert not result.largest_position_includes_cash
    assert not result.hhi_includes_cash
    assert result.long_only
    assert result.weight_sum_tolerance == WEIGHT_SUM_TOLERANCE


def test_equal_weight_portfolio_has_expected_largest_weight_and_hhi() -> None:
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=(0.25, 0.25, 0.25, 0.25),
        )
    )

    assert result.largest_position_weight == 0.25
    assert result.herfindahl_hirschman_index == 0.25


def test_cash_is_reported_separately_and_excluded_from_default_hhi() -> None:
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=(0.50, 0.40),
            cash_weight=0.10,
        )
    )

    assert result.largest_position_weight == 0.50
    assert result.herfindahl_hirschman_index == pytest.approx(0.41)
    assert result.cash_weight == 0.10
    assert not result.hhi_includes_cash


def test_cash_only_portfolio_has_no_largest_security_position() -> None:
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=(),
            cash_weight=1.0,
        )
    )

    assert result.largest_position_weight is None
    assert result.herfindahl_hirschman_index == 0.0
    assert result.security_position_count == 0


def test_weights_within_sum_tolerance_are_accepted_without_renormalization() -> None:
    supplied = (0.60, 0.399999995)
    weights = NormalizedPortfolioWeights(
        security_weights=supplied,
    )
    result = portfolio_concentration(weights)

    assert weights.security_weights == supplied
    assert result.largest_position_weight == 0.60
    assert result.herfindahl_hirschman_index == pytest.approx(0.60**2 + 0.399999995**2)


def test_materially_invalid_weight_sum_is_rejected() -> None:
    with pytest.raises(ValueError, match="must sum to one"):
        NormalizedPortfolioWeights(
            security_weights=(0.50, 0.40),
        )


@pytest.mark.parametrize(
    "security_weights",
    [
        (-0.01, 1.01),
        (float("nan"), 1.0),
        (float("inf"), 0.0),
    ],
)
def test_invalid_security_weights_are_rejected(
    security_weights: tuple[float, float],
) -> None:
    with pytest.raises(ValueError):
        NormalizedPortfolioWeights(
            security_weights=security_weights,
        )


def test_negative_cash_is_rejected() -> None:
    with pytest.raises(ValueError, match="cash_weight"):
        NormalizedPortfolioWeights(
            security_weights=(1.0,),
            cash_weight=-0.01,
        )
