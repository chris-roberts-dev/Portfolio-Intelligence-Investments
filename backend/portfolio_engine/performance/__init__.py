"""Framework-independent portfolio performance calculations."""

from portfolio_engine.performance.returns import (
    AnnualizedReturnResult,
    ReturnSeries,
    annualized_geometric_return,
    cagr,
    cumulative_return,
    log_returns,
    rolling_cumulative_returns,
    simple_returns,
)

__all__ = [
    "AnnualizedReturnResult",
    "ReturnSeries",
    "annualized_geometric_return",
    "cagr",
    "cumulative_return",
    "log_returns",
    "rolling_cumulative_returns",
    "simple_returns",
]
