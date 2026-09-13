"""Application orchestration for normalized market-bar queries.

Development guide references: Sections 8.4, 9.1, 9.2, and 9.7.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from apps.market_data.contracts import (
    MarketBarBatchMeta,
    MarketBarBatchResult,
    MarketBarStatus,
    MarketBarSymbolResult,
    NormalizedMarketBarQuery,
)
from apps.market_data.providers.base import (
    MarketDataProvider,
    ProviderIssue,
)
from apps.market_data.services.asset_resolution import (
    AssetResolver,
    ResolvedAssetSymbol,
    UnresolvedAssetSymbol,
)
from portfolio_engine.config import MAX_BAR_QUERY_ROWS
from portfolio_engine.contracts.market_data import PriceFrame
from portfolio_engine.contracts.market_data_validation import (
    MarketDataQualityError,
    validate_price_frame,
)


class MarketBarOrchestrationErrorCode(StrEnum):
    """Stable failures raised while constructing an application batch result."""

    ACTUAL_ROW_LIMIT_EXCEEDED = "ACTUAL_ROW_LIMIT_EXCEEDED"


class MarketBarOrchestrationError(ValueError):
    """Raised when provider output cannot satisfy an application-level limit."""

    def __init__(
        self,
        code: MarketBarOrchestrationErrorCode,
        message: str,
        *,
        actual_rows: int,
        max_rows: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.actual_rows = actual_rows
        self.max_rows = max_rows


def execute_market_bar_query(
    query: NormalizedMarketBarQuery,
    *,
    resolver: AssetResolver,
    provider: MarketDataProvider,
    max_rows: int = MAX_BAR_QUERY_ROWS,
) -> MarketBarBatchResult:
    """Resolve, retrieve, validate, and map one normalized market-bar query.

    The provider is already selected before this service is called. This
    function performs no provider fallback, persistence, caching, network
    configuration, authentication, or transport serialization.
    """
    if max_rows < 1:
        raise ValueError("max_rows must be positive")

    provider_name = provider.name.strip().lower()

    if not provider_name:
        raise ValueError("provider.name must not be blank")

    resolution = resolver.resolve(
        query.symbols,
        provider=provider_name,
    )

    provider_result = provider.get_daily_bars(
        resolution.provider_assets,
        query.start,
        query.end,
    )

    results: list[MarketBarSymbolResult] = []
    actual_rows = 0

    for outcome in resolution.outcomes:
        if isinstance(outcome, UnresolvedAssetSymbol):
            results.append(
                MarketBarSymbolResult(
                    symbol=outcome.requested_symbol.symbol,
                    asset_id=None,
                    status=MarketBarStatus.NOT_FOUND,
                )
            )
            continue

        result = _map_resolved_outcome(
            outcome,
            provider_name=provider_name,
            retrieved_at=provider_result.retrieved_at,
            frames=provider_result.frames,
            issues=provider_result.issues,
        )

        if result.status is MarketBarStatus.SUCCEEDED:
            actual_rows += len(result.bars)

            if actual_rows > max_rows:
                raise MarketBarOrchestrationError(
                    MarketBarOrchestrationErrorCode.ACTUAL_ROW_LIMIT_EXCEEDED,
                    (f"Actual provider output exceeds the configured {max_rows}-row limit."),
                    actual_rows=actual_rows,
                    max_rows=max_rows,
                )

        results.append(result)

    return MarketBarBatchResult(
        results=tuple(results),
        meta=MarketBarBatchMeta(
            provider=provider_name,
            retrieved_at=provider_result.retrieved_at,
            interval=query.interval,
            start=query.start,
            end=query.end,
        ),
    )


def _map_resolved_outcome(
    outcome: ResolvedAssetSymbol,
    *,
    provider_name: str,
    retrieved_at: datetime,
    frames: Mapping[UUID, PriceFrame],
    issues: Mapping[UUID, ProviderIssue],
) -> MarketBarSymbolResult:
    issue = issues.get(outcome.asset_id)

    if issue is not None:
        status = (
            MarketBarStatus.NO_DATA
            if str(issue.code).upper() == "NO_DATA"
            else MarketBarStatus.FAILED
        )

        return MarketBarSymbolResult(
            symbol=outcome.requested_symbol.symbol,
            asset_id=outcome.asset_id,
            status=status,
            warnings=(issue.message,),
        )

    frame = frames.get(outcome.asset_id)

    if frame is None:
        return MarketBarSymbolResult(
            symbol=outcome.requested_symbol.symbol,
            asset_id=outcome.asset_id,
            status=MarketBarStatus.FAILED,
            warnings=("Provider returned neither bars nor an issue for the resolved asset.",),
        )

    if not frame:
        return MarketBarSymbolResult(
            symbol=outcome.requested_symbol.symbol,
            asset_id=outcome.asset_id,
            status=MarketBarStatus.NO_DATA,
            warnings=("Provider returned no bars for the requested period.",),
        )

    try:
        validate_price_frame(frame)
        _validate_frame_provenance(
            frame,
            asset_id=outcome.asset_id,
            provider_name=provider_name,
            retrieved_at=retrieved_at,
        )
    except (MarketDataQualityError, ValueError) as exc:
        return MarketBarSymbolResult(
            symbol=outcome.requested_symbol.symbol,
            asset_id=outcome.asset_id,
            status=MarketBarStatus.FAILED,
            warnings=(str(exc),),
        )

    return MarketBarSymbolResult(
        symbol=outcome.requested_symbol.symbol,
        asset_id=outcome.asset_id,
        status=MarketBarStatus.SUCCEEDED,
        bars=frame,
    )


def _validate_frame_provenance(
    frame: PriceFrame,
    *,
    asset_id: UUID,
    provider_name: str,
    retrieved_at: datetime,
) -> None:
    for bar in frame:
        if bar.asset_id != asset_id:
            raise ValueError("Provider frame asset_id does not match the resolved internal asset.")

        if bar.source != provider_name:
            raise ValueError("Provider frame source does not match the resolved provider.")

        if bar.retrieved_at != retrieved_at:
            raise ValueError("Provider frame retrieved_at does not match batch provenance.")
