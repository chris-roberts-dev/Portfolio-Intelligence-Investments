import math
from datetime import date
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.portfolio.return_attribution import (
    AssetPeriodValueChange,
    attribute_daily_portfolio_return,
    link_daily_return_attributions,
)

VALUE = st.floats(
    min_value=0.0,
    max_value=1_000_000.0,
    allow_nan=False,
    allow_infinity=False,
)
FLOW = st.floats(
    min_value=-100_000.0,
    max_value=100_000.0,
    allow_nan=False,
    allow_infinity=False,
)
PORTFOLIO_RETURN = st.floats(
    min_value=-0.95,
    max_value=2.0,
    allow_nan=False,
    allow_infinity=False,
)


def _asset_inputs(
    rows: list[
        tuple[
            float,
            float,
            float,
        ]
    ],
) -> tuple[AssetPeriodValueChange, ...]:
    return tuple(
        AssetPeriodValueChange(
            asset_id=UUID(int=index + 1),
            starting_market_value=starting_value,
            ending_market_value=ending_value,
            internal_cash_flow=internal_cash_flow,
        )
        for index, (
            starting_value,
            ending_value,
            internal_cash_flow,
        ) in enumerate(rows)
    )


ASSET_INPUTS = st.lists(
    st.tuples(
        VALUE,
        VALUE,
        FLOW,
    ),
    min_size=0,
    max_size=12,
).map(_asset_inputs)


@given(
    assets=ASSET_INPUTS,
    prior_value=st.floats(
        min_value=1.0,
        max_value=10_000_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    portfolio_return=PORTFOLIO_RETURN,
)
def test_daily_asset_plus_residual_always_reconciles_to_portfolio_return(
    assets: tuple[AssetPeriodValueChange, ...],
    prior_value: float,
    portfolio_return: float,
) -> None:
    result = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=prior_value,
        portfolio_return=portfolio_return,
        assets=assets,
    )

    reconciled = math.fsum(
        (
            result.asset_contribution_total,
            result.unattributed_contribution,
        )
    )
    cancellation_tolerance = max(
        1e-12,
        math.ulp(result.asset_contribution_total),
        math.ulp(result.unattributed_contribution),
    )

    assert abs(reconciled - result.portfolio_return) <= cancellation_tolerance


@given(
    assets=ASSET_INPUTS,
    prior_value=st.floats(
        min_value=1.0,
        max_value=10_000_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    portfolio_return=PORTFOLIO_RETURN,
)
def test_daily_attribution_is_invariant_to_asset_input_permutation(
    assets: tuple[AssetPeriodValueChange, ...],
    prior_value: float,
    portfolio_return: float,
) -> None:
    original = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=prior_value,
        portfolio_return=portfolio_return,
        assets=assets,
    )
    reversed_result = attribute_daily_portfolio_return(
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 5),
        prior_portfolio_value=prior_value,
        portfolio_return=portfolio_return,
        assets=tuple(reversed(assets)),
    )

    assert reversed_result.asset_contributions == original.asset_contributions
    assert reversed_result.asset_contribution_total == pytest.approx(
        original.asset_contribution_total
    )
    assert reversed_result.unattributed_contribution == pytest.approx(
        original.unattributed_contribution
    )


@given(
    returns=st.lists(
        st.floats(
            min_value=-0.5,
            max_value=0.5,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=20,
    ).map(tuple)
)
def test_linked_contributions_reconcile_to_chain_linked_return(
    returns: tuple[float, ...],
) -> None:
    results = []
    start = date(2026, 1, 1)

    for index, portfolio_return in enumerate(returns):
        result = attribute_daily_portfolio_return(
            period_start=date.fromordinal(start.toordinal() + index),
            period_end=date.fromordinal(start.toordinal() + index + 1),
            prior_portfolio_value=100.0,
            portfolio_return=portfolio_return,
            assets=(
                AssetPeriodValueChange(
                    asset_id=UUID(int=1),
                    starting_market_value=0.0,
                    ending_market_value=0.0,
                    internal_cash_flow=(50.0 * portfolio_return),
                ),
                AssetPeriodValueChange(
                    asset_id=UUID(int=2),
                    starting_market_value=0.0,
                    ending_market_value=0.0,
                    internal_cash_flow=(50.0 * portfolio_return),
                ),
            ),
        )
        results.append(result)

    linked = link_daily_return_attributions(tuple(results))
    expected = math.prod(1.0 + value for value in returns) - 1.0
    reconciled = math.fsum(
        (
            linked.asset_contribution_total,
            linked.unattributed_contribution,
        )
    )

    assert linked.cumulative_return == pytest.approx(
        expected,
        rel=1e-12,
        abs=1e-12,
    )
    assert reconciled == pytest.approx(
        expected,
        rel=1e-12,
        abs=1e-12,
    )
