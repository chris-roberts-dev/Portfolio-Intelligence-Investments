"""Unit tests for the analytical result provenance envelope."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from portfolio_engine.contracts.analytical_result import AnalyticalResultProvenance
from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION


def make_provenance(
    *,
    as_of_date: date = date(2026, 1, 5),
    period_start: date = date(2025, 1, 1),
    period_end: date = date(2025, 12, 31),
    data_source: str = "yfinance",
    price_field: str = "adjusted_close",
    annualization_factor: float = 252.0,
    benchmark: str | None = "SPY",
    assumptions: tuple[str, ...] = ("Daily observations", "No cash flows"),
    warnings: tuple[str, ...] = ("Benchmark has shorter history",),
    engine_version: str = PORTFOLIO_ENGINE_VERSION,
) -> AnalyticalResultProvenance:
    return AnalyticalResultProvenance(
        as_of_date=as_of_date,
        period_start=period_start,
        period_end=period_end,
        data_source=data_source,
        price_field=price_field,
        annualization_factor=annualization_factor,
        benchmark=benchmark,
        assumptions=assumptions,
        warnings=warnings,
        engine_version=engine_version,
    )


def test_provenance_defaults_to_centralized_engine_version() -> None:
    provenance = AnalyticalResultProvenance(
        as_of_date=date(2026, 1, 5),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        data_source="yfinance",
        price_field="adjusted_close",
        annualization_factor=252.0,
    )

    assert provenance.engine_version == PORTFOLIO_ENGINE_VERSION


def test_provenance_preserves_assumption_and_warning_order() -> None:
    assumptions = ("first assumption", "second assumption", "third assumption")
    warnings = ("first warning", "second warning")

    provenance = make_provenance(
        assumptions=assumptions,
        warnings=warnings,
    )

    assert provenance.assumptions == assumptions
    assert provenance.warnings == warnings


def test_provenance_is_immutable() -> None:
    provenance = make_provenance()

    with pytest.raises(FrozenInstanceError):
        provenance.data_source = "other"


def test_period_start_must_not_follow_period_end() -> None:
    with pytest.raises(ValueError, match="period_start"):
        make_provenance(
            period_start=date(2026, 1, 2),
            period_end=date(2026, 1, 1),
        )


@pytest.mark.parametrize(
    "annualization_factor",
    [0.0, -1.0, float("inf"), float("nan")],
)
def test_annualization_factor_must_be_finite_and_positive(
    annualization_factor: float,
) -> None:
    with pytest.raises(ValueError, match="annualization_factor"):
        make_provenance(annualization_factor=annualization_factor)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("engine_version", "   "),
        ("data_source", ""),
        ("price_field", "   "),
        ("benchmark", "   "),
    ],
)
def test_provenance_strings_must_not_be_blank(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        if field_name == "engine_version":
            make_provenance(engine_version=value)
        elif field_name == "data_source":
            make_provenance(data_source=value)
        elif field_name == "price_field":
            make_provenance(price_field=value)
        else:
            make_provenance(benchmark=value)


def test_benchmark_may_be_omitted() -> None:
    provenance = make_provenance(benchmark=None)

    assert provenance.benchmark is None


@pytest.mark.parametrize(
    ("field_name", "values"),
    [
        ("assumptions", ("valid", "   ")),
        ("warnings", ("",)),
    ],
)
def test_assumptions_and_warnings_reject_blank_items(
    field_name: str,
    values: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match=field_name):
        if field_name == "assumptions":
            make_provenance(assumptions=values)
        else:
            make_provenance(warnings=values)
