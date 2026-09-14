"""Property tests for volatility and Sharpe-ratio calculations."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from portfolio_engine.config import TRADING_DAYS_PER_YEAR
from portfolio_engine.performance.statistics import (
    annual_effective_rate_to_daily,
    annualized_volatility,
    sample_standard_deviation,
    sharpe_ratio,
)

INTEGER_SERIES = st.lists(
    st.integers(min_value=-1000, max_value=1000),
    min_size=2,
    max_size=30,
).map(tuple)


@given(
    values=INTEGER_SERIES,
    shift=st.integers(min_value=-1000, max_value=1000),
)
def test_sample_standard_deviation_is_location_invariant(
    values: tuple[int, ...],
    shift: int,
) -> None:
    base = tuple(float(value) for value in values)
    shifted = tuple(float(value + shift) for value in values)

    assert sample_standard_deviation(shifted) == pytest.approx(
        sample_standard_deviation(base),
        rel=1e-12,
        abs=1e-12,
    )


@given(
    values=INTEGER_SERIES,
    scale=st.integers(min_value=-10, max_value=10).filter(lambda value: value != 0),
)
def test_sample_standard_deviation_scales_by_absolute_factor(
    values: tuple[int, ...],
    scale: int,
) -> None:
    base = tuple(float(value) for value in values)
    scaled = tuple(float(value * scale) for value in values)

    assert sample_standard_deviation(scaled) == pytest.approx(
        abs(scale) * sample_standard_deviation(base),
        rel=1e-12,
        abs=1e-12,
    )


@given(values=INTEGER_SERIES)
def test_annualized_volatility_matches_sample_deviation_times_sqrt_252(
    values: tuple[int, ...],
) -> None:
    daily_returns = tuple(value / 10_000.0 for value in values)

    assert annualized_volatility(daily_returns) == pytest.approx(
        sample_standard_deviation(daily_returns) * TRADING_DAYS_PER_YEAR**0.5,
        rel=1e-12,
        abs=1e-12,
    )


@given(
    annual_rate=st.integers(min_value=-9000, max_value=20_000).map(
        lambda basis_points: basis_points / 10_000.0
    )
)
def test_daily_effective_rate_recompounds_to_annual_effective_rate(
    annual_rate: float,
) -> None:
    daily_rate = annual_effective_rate_to_daily(annual_rate)
    recomposed = (1.0 + daily_rate) ** TRADING_DAYS_PER_YEAR - 1.0

    assert recomposed == pytest.approx(annual_rate, rel=1e-11, abs=1e-12)


@given(
    values=INTEGER_SERIES,
    scale=st.integers(min_value=1, max_value=10),
)
def test_zero_risk_free_sharpe_is_invariant_to_positive_scaling(
    values: tuple[int, ...],
    scale: int,
) -> None:
    returns = tuple(value / 10_000.0 for value in values)
    assume(sample_standard_deviation(returns) > 0.0)

    scaled_returns = tuple(value * scale for value in returns)
    base = sharpe_ratio(returns, risk_free_rate_annual=0.0)
    scaled = sharpe_ratio(scaled_returns, risk_free_rate_annual=0.0)

    assert base.value is not None
    assert scaled.value == pytest.approx(base.value, rel=1e-11, abs=1e-12)


@given(
    prefix=INTEGER_SERIES,
    future=st.lists(
        st.integers(min_value=-1000, max_value=1000),
        max_size=20,
    ).map(tuple),
)
def test_prefix_statistics_do_not_depend_on_future_observations(
    prefix: tuple[int, ...],
    future: tuple[int, ...],
) -> None:
    prefix_returns = tuple(value / 10_000.0 for value in prefix)
    extended_returns = prefix_returns + tuple(value / 10_000.0 for value in future)
    same_prefix = extended_returns[: len(prefix_returns)]

    assert annualized_volatility(same_prefix) == annualized_volatility(prefix_returns)
    assert sharpe_ratio(
        same_prefix,
        risk_free_rate_annual=0.0,
    ) == sharpe_ratio(
        prefix_returns,
        risk_free_rate_annual=0.0,
    )
