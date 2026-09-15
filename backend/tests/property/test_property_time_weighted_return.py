"""Property tests for canonical daily time-weighted return."""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.performance.time_weighted import (
    DailyPortfolioValue,
    calculate_daily_time_weighted_return,
)

POSITIVE_VALUE = st.floats(
    min_value=1.0,
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
RETURN = st.floats(
    min_value=-0.95,
    max_value=2.0,
    allow_nan=False,
    allow_infinity=False,
)


@given(
    prior_value=POSITIVE_VALUE,
    net_flow=FLOW,
)
def test_external_flow_without_investment_gain_has_zero_return(
    prior_value: float,
    net_flow: float,
) -> None:
    ending_value = prior_value + net_flow

    result = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=prior_value,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=ending_value,
                net_external_flow=net_flow,
            ),
        )
    )

    assert result.cumulative_return == pytest.approx(
        0.0,
        abs=1e-10,
    )


@given(
    prior_value=POSITIVE_VALUE,
    net_flow=FLOW,
    daily_return=RETURN,
)
def test_daily_formula_recovers_constructed_return(
    prior_value: float,
    net_flow: float,
    daily_return: float,
) -> None:
    ending_value = prior_value * (1.0 + daily_return) + net_flow

    result = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=prior_value,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=ending_value,
                net_external_flow=net_flow,
            ),
        )
    )

    assert result.cumulative_return == pytest.approx(
        daily_return,
        rel=1e-10,
        abs=1e-10,
    )


@given(
    prior_value=POSITIVE_VALUE,
    net_flow=FLOW,
    daily_return=RETURN,
    scale=st.floats(
        min_value=0.01,
        max_value=100.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_daily_twr_is_invariant_to_common_value_scale(
    prior_value: float,
    net_flow: float,
    daily_return: float,
    scale: float,
) -> None:
    ending_value = prior_value * (1.0 + daily_return) + net_flow

    original = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=prior_value,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=ending_value,
                net_external_flow=net_flow,
            ),
        )
    )
    scaled = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=prior_value * scale,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=ending_value * scale,
                net_external_flow=net_flow * scale,
            ),
        )
    )

    assert scaled.cumulative_return == pytest.approx(
        original.cumulative_return,
        rel=1e-10,
        abs=1e-10,
    )


@given(
    first_return=RETURN,
    second_return=RETURN,
)
def test_future_observation_does_not_change_prior_daily_return(
    first_return: float,
    second_return: float,
) -> None:
    start_value = 100.0
    second_value = start_value * (1.0 + first_return)
    third_value = second_value * (1.0 + second_return)

    prefix = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=start_value,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=second_value,
            ),
        )
    )
    extended = calculate_daily_time_weighted_return(
        (
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 2),
                portfolio_value=start_value,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 5),
                portfolio_value=second_value,
            ),
            DailyPortfolioValue(
                valuation_date=date(2026, 1, 6),
                portfolio_value=third_value,
            ),
        )
    )

    assert extended.daily_returns[0] == prefix.daily_returns[0]
