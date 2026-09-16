import { useQuery } from "@tanstack/react-query";

import { fetchMarketBars } from "../api/marketData";
import type { MarketBarQueryRequest } from "../types/marketData";

export function marketBarQueryKey(
  request: MarketBarQueryRequest | null,
) {
  return request === null
    ? ["market-data", "bars", "disabled"] as const
    : [
        "market-data",
        "bars",
        request.symbols,
        request.start,
        request.end,
        request.interval,
        request.provider ?? null,
      ] as const;
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
    staleTime: 30_000,
  });
}
