import { apiGet, apiPost } from "./client";
import type {
  OptimizationRun,
  OptimizationRunCreateRequest,
} from "../types/optimization";

export function fetchOptimizationRuns(
  signal?: AbortSignal,
): Promise<OptimizationRun[]> {
  return apiGet<OptimizationRun[]>("/api/v1/optimization-runs/", {
    signal,
  });
}

export function fetchOptimizationRun(
  runId: string,
  signal?: AbortSignal,
): Promise<OptimizationRun> {
  return apiGet<OptimizationRun>(
    `/api/v1/optimization-runs/${encodeURIComponent(runId)}/`,
    { signal },
  );
}

export function createOptimizationRun(
  request: OptimizationRunCreateRequest,
  signal?: AbortSignal,
): Promise<OptimizationRun> {
  return apiPost<OptimizationRun, OptimizationRunCreateRequest>(
    "/api/v1/optimization-runs/",
    request,
    { signal },
  );
}
