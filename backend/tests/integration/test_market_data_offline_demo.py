"""Regression coverage for the deterministic offline market-data demonstration."""

from apps.market_data.contracts import MarketBarStatus
from scripts.market_data_offline_demo import (
    EXPECTED_SYMBOLS,
    build_offline_demo_result,
    validate_offline_demo_result,
)


def test_offline_market_data_demo_proves_ordered_partial_results() -> None:
    result = build_offline_demo_result()

    validate_offline_demo_result(result)

    assert tuple(item.symbol for item in result.results) == EXPECTED_SYMBOLS
    assert tuple(item.status for item in result.results) == (
        MarketBarStatus.SUCCEEDED,
        MarketBarStatus.SUCCEEDED,
        MarketBarStatus.NO_DATA,
        MarketBarStatus.NOT_FOUND,
    )
    assert result.row_count == 10
    assert result.meta.provider == "csv"
