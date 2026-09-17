"""Canonical historical estimators for Phase 5 optimization.

Development guide references: Sections 11.1, 12.2, and 12.3.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np

from portfolio_engine.config import TRADING_DAYS_PER_YEAR
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.optimization.contracts import (
    HistoricalOptimizationEstimate,
    OptimizationError,
    OptimizationErrorCode,
)
from portfolio_engine.performance.returns import simple_returns


def estimate_historical_inputs(
    asset_keys: Sequence[str],
    frames: Mapping[str, PriceFrame],
) -> HistoricalOptimizationEstimate:
    """Estimate annual return and covariance from complete-case adjusted closes.

    Price dates are intersected across every requested asset before canonical
    simple returns are calculated. The resulting aligned daily-return matrix is
    therefore complete-case by construction. Expected returns use arithmetic
    daily means times 252; covariance uses sample covariance (ddof=1) times 252.
    """
    keys = tuple(asset_keys)
    if not keys or len(set(keys)) != len(keys):
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            "asset_keys must be non-empty and unique.",
        )

    missing = tuple(key for key in keys if key not in frames)
    if missing:
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            f"Missing price frames for assets: {missing!r}.",
        )

    adjusted_by_asset = {key: _adjusted_close_by_date(frames[key], asset_key=key) for key in keys}
    common_dates = set(adjusted_by_asset[keys[0]])
    for key in keys[1:]:
        common_dates.intersection_update(adjusted_by_asset[key])

    ordered_dates = tuple(sorted(common_dates))
    if len(ordered_dates) < 3:
        raise OptimizationError(
            OptimizationErrorCode.INSUFFICIENT_DATA,
            "At least three complete-case adjusted-close observations are required.",
        )

    per_asset_returns = []
    for key in keys:
        prices = tuple(adjusted_by_asset[key][trade_date] for trade_date in ordered_dates)
        per_asset_returns.append(simple_returns(prices))

    return_dates = ordered_dates[1:]
    return_matrix = np.column_stack(per_asset_returns).astype(float, copy=False)

    if return_matrix.shape[0] < 2:
        raise OptimizationError(
            OptimizationErrorCode.INSUFFICIENT_DATA,
            "At least two complete-case daily return observations are required.",
        )
    if not np.isfinite(return_matrix).all():
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            "Complete-case daily returns must be finite.",
        )

    expected = np.mean(return_matrix, axis=0) * TRADING_DAYS_PER_YEAR
    if len(keys) == 1:
        covariance_array = np.array(
            [[np.var(return_matrix[:, 0], ddof=1) * TRADING_DAYS_PER_YEAR]],
            dtype=float,
        )
    else:
        covariance_array = np.cov(return_matrix, rowvar=False, ddof=1) * TRADING_DAYS_PER_YEAR
        covariance_array = np.asarray(covariance_array, dtype=float)

    if not np.isfinite(expected).all() or not np.isfinite(covariance_array).all():
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            "Historical estimates must be finite.",
        )

    covariance_array = (covariance_array + covariance_array.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(covariance_array)
    if float(np.min(eigenvalues)) < -1e-10:
        raise OptimizationError(
            OptimizationErrorCode.INVALID_INPUT,
            "Historical covariance must be positive semidefinite within tolerance.",
        )

    return HistoricalOptimizationEstimate(
        asset_keys=keys,
        return_dates=tuple(return_dates),
        observations=return_matrix.shape[0],
        expected_returns=tuple(float(value) for value in expected),
        covariance=tuple(tuple(float(value) for value in row) for row in covariance_array),
        covariance_rank=int(np.linalg.matrix_rank(covariance_array, tol=1e-12)),
    )


def _adjusted_close_by_date(
    frame: PriceFrame,
    *,
    asset_key: str,
) -> dict[date, float]:
    observations: dict[date, float] = {}

    for bar in frame:
        value = bar.adjusted_close
        if value is None:
            continue
        number = float(value)
        if not math.isfinite(number) or number <= 0.0:
            raise OptimizationError(
                OptimizationErrorCode.INVALID_INPUT,
                f"Adjusted close for {asset_key!r} must be positive and finite.",
            )
        if bar.trade_date in observations:
            raise OptimizationError(
                OptimizationErrorCode.INVALID_INPUT,
                f"Duplicate adjusted-close date for {asset_key!r}: {bar.trade_date}.",
            )
        observations[bar.trade_date] = number

    return observations
