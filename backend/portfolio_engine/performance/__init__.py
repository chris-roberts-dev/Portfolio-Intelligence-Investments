"""Framework-independent portfolio performance calculations."""

from portfolio_engine.performance.returns import (
    ReturnSeries,
    cumulative_return,
    log_returns,
    simple_returns,
)

__all__ = [
    "ReturnSeries",
    "cumulative_return",
    "log_returns",
    "simple_returns",
]
