import { apiGet, apiPost } from "./client";
import type {
  HistoricalRebalanceComparison,
  HistoricalRebalanceComparisonCreateRequest,
  RebalanceSimulation,
  RebalanceSimulationCreateRequest,
  TargetAllocation,
  TargetAllocationCreateRequest,
} from "../types/rebalancing";

export function fetchTargetAllocations(
  signal?: AbortSignal,
): Promise<TargetAllocation[]> {
  return apiGet<TargetAllocation[]>("/api/v1/target-allocations/", { signal });
}

export function createTargetAllocation(
  request: TargetAllocationCreateRequest,
  signal?: AbortSignal,
): Promise<TargetAllocation> {
  return apiPost<TargetAllocation, TargetAllocationCreateRequest>(
    "/api/v1/target-allocations/",
    request,
    { signal },
  );
}

export function fetchRebalanceSimulations(
  signal?: AbortSignal,
): Promise<RebalanceSimulation[]> {
  return apiGet<RebalanceSimulation[]>("/api/v1/rebalance-simulations/", {
    signal,
  });
}

export function createRebalanceSimulation(
  request: RebalanceSimulationCreateRequest,
  signal?: AbortSignal,
): Promise<RebalanceSimulation> {
  return apiPost<RebalanceSimulation, RebalanceSimulationCreateRequest>(
    "/api/v1/rebalance-simulations/",
    request,
    { signal },
  );
}

export function fetchHistoricalRebalanceComparisons(
  signal?: AbortSignal,
): Promise<HistoricalRebalanceComparison[]> {
  return apiGet<HistoricalRebalanceComparison[]>(
    "/api/v1/historical-rebalance-comparisons/",
    { signal },
  );
}

export function createHistoricalRebalanceComparison(
  request: HistoricalRebalanceComparisonCreateRequest,
  signal?: AbortSignal,
): Promise<HistoricalRebalanceComparison> {
  return apiPost<
    HistoricalRebalanceComparison,
    HistoricalRebalanceComparisonCreateRequest
  >("/api/v1/historical-rebalance-comparisons/", request, { signal });
}
