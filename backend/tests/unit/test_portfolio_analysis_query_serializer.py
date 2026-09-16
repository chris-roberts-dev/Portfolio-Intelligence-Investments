from __future__ import annotations

import pytest

from apps.portfolios.api.contracts import PortfolioAnalysisQuerySerializer


def test_analysis_query_accepts_explicit_positive_rolling_window() -> None:
    serializer = PortfolioAnalysisQuerySerializer(
        data={
            "start": "2026-01-01",
            "end": "2026-09-16",
            "rolling_window": "21",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.rolling_window_value == 21


def test_analysis_query_has_no_hidden_rolling_window_default() -> None:
    serializer = PortfolioAnalysisQuerySerializer(
        data={
            "start": "2026-01-01",
            "end": "2026-09-16",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.rolling_window_value is None


@pytest.mark.parametrize(
    "rolling_window",
    ("0", "-1"),
)
def test_analysis_query_rejects_nonpositive_rolling_windows(
    rolling_window: str,
) -> None:
    serializer = PortfolioAnalysisQuerySerializer(
        data={
            "start": "2026-01-01",
            "end": "2026-09-16",
            "rolling_window": rolling_window,
        }
    )

    assert not serializer.is_valid()
    assert "rolling_window" in serializer.errors
