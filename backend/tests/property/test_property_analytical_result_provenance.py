"""Property tests for the analytical result provenance envelope."""

import string
from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st

from portfolio_engine.contracts.analytical_result import AnalyticalResultProvenance

NONBLANK_TEXT = st.text(
    alphabet=string.ascii_letters + string.digits + " -_",
    min_size=1,
).filter(lambda value: bool(value.strip()))


@given(
    period_start=st.dates(
        min_value=date(1970, 1, 1),
        max_value=date(2099, 12, 31),
    ),
    period_length=st.integers(min_value=0, max_value=3650),
    annualization_factor=st.floats(
        min_value=0.000001,
        max_value=10000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_valid_ordered_periods_and_positive_annualization_are_accepted(
    period_start: date,
    period_length: int,
    annualization_factor: float,
) -> None:
    period_end = period_start + timedelta(days=period_length)

    provenance = AnalyticalResultProvenance(
        as_of_date=period_end,
        period_start=period_start,
        period_end=period_end,
        data_source="test-source",
        price_field="adjusted_close",
        annualization_factor=annualization_factor,
    )

    assert provenance.period_start <= provenance.period_end
    assert provenance.annualization_factor > 0.0


@given(
    assumptions=st.lists(NONBLANK_TEXT, max_size=20).map(tuple),
    warnings=st.lists(NONBLANK_TEXT, max_size=20).map(tuple),
)
def test_assumptions_and_warnings_preserve_input_order(
    assumptions: tuple[str, ...],
    warnings: tuple[str, ...],
) -> None:
    provenance = AnalyticalResultProvenance(
        as_of_date=date(2026, 1, 1),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        data_source="test-source",
        price_field="adjusted_close",
        annualization_factor=252.0,
        assumptions=assumptions,
        warnings=warnings,
    )

    assert provenance.assumptions == assumptions
    assert provenance.warnings == warnings
