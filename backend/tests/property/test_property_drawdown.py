"""Property tests for wealth-index and drawdown calculations."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.performance.drawdown import (
    drawdown_series,
    maximum_drawdown,
    running_peak,
    wealth_index,
)

RETURN_SERIES = st.lists(
    st.integers(min_value=-9000, max_value=10_000),
    min_size=1,
    max_size=30,
).map(lambda values: tuple(value / 10_000.0 for value in values))

PREFIX_FUTURE_CASE = RETURN_SERIES.flatmap(
    lambda prefix: st.tuples(
        st.just(prefix),
        st.lists(
            st.integers(min_value=-9000, max_value=10_000),
            max_size=15,
        ).map(lambda values: tuple(value / 10_000.0 for value in values)),
    )
)


@given(returns=RETURN_SERIES)
def test_drawdowns_are_never_positive(
    returns: tuple[float, ...],
) -> None:
    drawdowns = drawdown_series(wealth_index(returns))

    assert all(drawdown <= 1e-12 for drawdown in drawdowns)


@given(returns=RETURN_SERIES)
def test_drawdown_is_zero_at_running_highs(
    returns: tuple[float, ...],
) -> None:
    wealth = wealth_index(returns)
    peaks = running_peak(wealth)
    drawdowns = drawdown_series(wealth)

    for wealth_value, peak, drawdown in zip(
        wealth,
        peaks,
        drawdowns,
        strict=True,
    ):
        if wealth_value == peak:
            assert drawdown == pytest.approx(0.0, abs=1e-12)


@given(returns=RETURN_SERIES)
def test_maximum_drawdown_matches_minimum_drawdown_series(
    returns: tuple[float, ...],
) -> None:
    wealth = wealth_index(returns)
    drawdowns = drawdown_series(wealth)
    result = maximum_drawdown(returns)

    assert result.value is not None
    assert result.value == pytest.approx(min(drawdowns))

    assert result.peak_index is not None
    assert result.trough_index is not None
    assert result.peak_index <= result.trough_index
    assert wealth[result.peak_index] == max(wealth[: result.trough_index + 1])
    assert result.value == pytest.approx(
        wealth[result.trough_index] / wealth[result.peak_index] - 1.0
    )


@given(case=PREFIX_FUTURE_CASE)
def test_drawdown_paths_do_not_depend_on_future_observations(
    case: tuple[tuple[float, ...], tuple[float, ...]],
) -> None:
    prefix, future = case
    prefix_wealth = wealth_index(prefix)
    full_wealth = wealth_index(prefix + future)

    assert full_wealth[: len(prefix_wealth)] == pytest.approx(prefix_wealth)

    prefix_peaks = running_peak(prefix_wealth)
    full_peaks = running_peak(full_wealth)

    assert full_peaks[: len(prefix_peaks)] == pytest.approx(prefix_peaks)

    prefix_drawdowns = drawdown_series(prefix_wealth)
    full_drawdowns = drawdown_series(full_wealth)

    assert full_drawdowns[: len(prefix_drawdowns)] == pytest.approx(prefix_drawdowns)
