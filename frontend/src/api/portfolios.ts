import { apiGet } from "./client";
import type {
  DashboardSnapshotResult,
  PortfolioListItem,
} from "../types/dashboard";

export interface DashboardSnapshotRequest {
  portfolioId: string;
  start: string;
  end: string;
}

export function fetchPortfolios(signal?: AbortSignal): Promise<PortfolioListItem[]> {
  return apiGet<PortfolioListItem[]>("/api/v1/portfolios/", { signal });
}

export function fetchDashboardSnapshot(
  request: DashboardSnapshotRequest,
  signal?: AbortSignal,
): Promise<DashboardSnapshotResult> {
  const params = new URLSearchParams({
    start: request.start,
    end: request.end,
  });
  const portfolioId = encodeURIComponent(request.portfolioId);

  return apiGet<DashboardSnapshotResult>(
    `/api/v1/portfolios/${portfolioId}/dashboard/?${params.toString()}`,
    { signal },
  );
}
