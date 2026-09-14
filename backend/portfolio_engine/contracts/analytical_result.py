"""Framework-independent analytical result provenance contracts.

Development guide reference: Section 8.8.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from portfolio_engine.version import PORTFOLIO_ENGINE_VERSION

type BenchmarkIdentity = str


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyticalResultProvenance:
    """Immutable provenance envelope shared by analytical engine results."""

    as_of_date: date
    period_start: date
    period_end: date
    data_source: str
    price_field: str
    annualization_factor: float
    benchmark: BenchmarkIdentity | None = None
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    engine_version: str = PORTFOLIO_ENGINE_VERSION

    def __post_init__(self) -> None:
        if self.period_start > self.period_end:
            raise ValueError("period_start must not be after period_end")

        if not math.isfinite(self.annualization_factor) or self.annualization_factor <= 0.0:
            raise ValueError("annualization_factor must be finite and positive")

        _require_nonblank("engine_version", self.engine_version)
        _require_nonblank("data_source", self.data_source)
        _require_nonblank("price_field", self.price_field)

        if self.benchmark is not None:
            _require_nonblank("benchmark", self.benchmark)

        _require_nonblank_items("assumptions", self.assumptions)
        _require_nonblank_items("warnings", self.warnings)


def _require_nonblank(field_name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


def _require_nonblank_items(field_name: str, values: tuple[str, ...]) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} must not contain blank values")
