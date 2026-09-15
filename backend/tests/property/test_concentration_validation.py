"""Independent validation fixtures for portfolio concentration metrics."""

import pytest

from portfolio_engine.risk.concentration import (
    NormalizedPortfolioWeights,
    portfolio_concentration,
)


def test_known_three_security_fixture_matches_manual_concentration() -> None:
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=(0.50, 0.30, 0.20),
        )
    )

    assert result.largest_position_weight == 0.50
    assert result.herfindahl_hirschman_index == pytest.approx(0.50**2 + 0.30**2 + 0.20**2)
    assert result.herfindahl_hirschman_index == pytest.approx(0.38)


def test_known_cash_fixture_excludes_cash_without_security_renormalization() -> None:
    result = portfolio_concentration(
        NormalizedPortfolioWeights(
            security_weights=(0.50, 0.40),
            cash_weight=0.10,
        )
    )

    security_only_hhi = 0.50**2 + 0.40**2
    hhi_if_cash_were_included = security_only_hhi + 0.10**2

    assert result.herfindahl_hirschman_index == pytest.approx(security_only_hhi)
    assert result.herfindahl_hirschman_index != pytest.approx(hhi_if_cash_were_included)
