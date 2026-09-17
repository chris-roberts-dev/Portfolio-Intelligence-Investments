import { useQuery } from "@tanstack/react-query";

import { fetchMarketBars } from "../api/marketData";
import type { MarketBarQueryRequest } from "../types/marketData";

export const MARKET_DATA_STALE_TIME_MS = 5 * 60 * 1000;
export const MARKET_DATA_GC_TIME_MS = 30 * 60 * 1000;

export function marketBarQueryKey(
  request: MarketBarQueryRequest | null,
) {
  return request === null
    ? (["market-data", "bars", "disabled"] as const)
    : ([
        "market-data",
        "bars",
        request.symbols,
        request.start,
        request.end,
        request.interval,
        request.provider ?? null,
      ] as const);
}

export function useMarketBarQuery(
  request: MarketBarQueryRequest | null,
) {
  return useQuery({
    queryKey: marketBarQueryKey(request),
    queryFn: ({ signal }) => {
      if (request === null) {
        throw new Error("Market-data request is not available.");
      }

      return fetchMarketBars(request, signal);
    },
    enabled: request !== null,
    retry: 1,

    // Historical market-data responses are stable enough to remain fresh
    // locally for several minutes. Explicit Query/Retry actions remain the
    // authoritative way to request fresh provider data.
    staleTime: MARKET_DATA_STALE_TIME_MS,

    // Keep inactive queries in memory so navigating elsewhere in the app for
    // a short period does not immediately discard potentially large responses.
    gcTime: MARKET_DATA_GC_TIME_MS,

    // Market Data Explorer uses explicit submission. Changing browser focus,
    // restoring connectivity, or remounting the query must not unexpectedly
    // generate another live-provider request.
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
}