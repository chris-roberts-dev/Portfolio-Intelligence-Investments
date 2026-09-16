import { apiPost } from "./client";
import type {
  MarketBarBatchResult,
  MarketBarQueryRequest,
} from "../types/marketData";

export function fetchMarketBars(
  request: MarketBarQueryRequest,
  signal?: AbortSignal,
): Promise<MarketBarBatchResult> {
  return apiPost<MarketBarBatchResult, MarketBarQueryRequest>(
    "/api/v1/market-data/bars/query/",
    request,
    { signal },
  );
}
