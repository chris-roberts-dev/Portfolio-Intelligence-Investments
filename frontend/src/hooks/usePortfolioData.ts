import { useQuery } from "@tanstack/react-query";

import {
  fetchDashboardSnapshot,
  fetchPortfolios,
  type DashboardSnapshotRequest,
} from "../api/portfolios";

export function usePortfolios() {
  return useQuery({
    queryKey: ["portfolios"],
    queryFn: ({ signal }) => fetchPortfolios(signal),
    staleTime: 30_000,
  });
}

export function useDashboardSnapshot(
  request: DashboardSnapshotRequest | null,
) {
  return useQuery({
    queryKey: request === null
      ? ["portfolio-dashboard", "disabled"]
      : [
          "portfolio-dashboard",
          request.portfolioId,
          request.start,
          request.end,
        ],
    queryFn: ({ signal }) => {
      if (request === null) {
        throw new Error("Dashboard snapshot request is not available.");
      }

      return fetchDashboardSnapshot(request, signal);
    },
    enabled: request !== null,
    retry: 1,
    staleTime: 30_000,
  });
}
