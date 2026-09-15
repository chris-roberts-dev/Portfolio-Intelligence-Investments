"""Framework-independent portfolio calculations."""

from portfolio_engine.portfolio.allocation import (
    PortfolioAllocationResult,
    SecurityAllocation,
    derive_portfolio_allocation,
)
from portfolio_engine.portfolio.return_attribution import (
    AssetPeriodValueChange,
    DailyAssetReturnContribution,
    DailyReturnAttributionResult,
    LinkedAssetReturnContribution,
    LinkedReturnAttributionResult,
    ReturnAttributionError,
    attribute_daily_portfolio_return,
    link_daily_return_attributions,
)
from portfolio_engine.portfolio.valuation import (
    AssetPositionValuationInput,
    PortfolioValuationResult,
    PositionValuationResult,
    value_portfolio,
    value_position,
)
from portfolio_engine.portfolio.weighted_returns import (
    DatedAssetReturn,
    HypotheticalWeightedReturnResult,
    PortfolioReturnAlignmentError,
    PortfolioWeightError,
    PriorPeriodAssetWeight,
    hypothetical_weighted_portfolio_return,
)

__all__ = [
    "AssetPeriodValueChange",
    "AssetPositionValuationInput",
    "DailyAssetReturnContribution",
    "DailyReturnAttributionResult",
    "DatedAssetReturn",
    "HypotheticalWeightedReturnResult",
    "LinkedAssetReturnContribution",
    "LinkedReturnAttributionResult",
    "PortfolioAllocationResult",
    "PortfolioReturnAlignmentError",
    "PortfolioValuationResult",
    "PortfolioWeightError",
    "PositionValuationResult",
    "PriorPeriodAssetWeight",
    "ReturnAttributionError",
    "SecurityAllocation",
    "attribute_daily_portfolio_return",
    "derive_portfolio_allocation",
    "hypothetical_weighted_portfolio_return",
    "link_daily_return_attributions",
    "value_portfolio",
    "value_position",
]
