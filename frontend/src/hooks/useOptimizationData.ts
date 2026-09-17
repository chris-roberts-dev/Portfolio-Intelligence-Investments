import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createOptimizationRun,
  fetchOptimizationRun,
  fetchOptimizationRuns,
} from "../api/optimization";
import type {
  OptimizationRun,
  OptimizationRunCreateRequest,
} from "../types/optimization";

const OPTIMIZATION_RUNS_ROOT_QUERY_KEY = ["optimization-runs"] as const;

export function optimizationRunsQueryKey(portfolioId: string | null) {
  return [
    ...OPTIMIZATION_RUNS_ROOT_QUERY_KEY,
    "portfolio",
    portfolioId ?? "disabled",
  ] as const;
}

export function optimizationRunDetailQueryKey(runId: string | null) {
  return [
    ...OPTIMIZATION_RUNS_ROOT_QUERY_KEY,
    "detail",
    runId ?? "disabled",
  ] as const;
}

export function useOptimizationRuns(portfolioId: string | null) {
  return useQuery({
    queryKey: optimizationRunsQueryKey(portfolioId),
    queryFn: async ({ signal }) => {
      if (portfolioId === null) {
        throw new Error("Portfolio optimization-run list is not available.");
      }

      const runs = await fetchOptimizationRuns(signal);
      return runs.filter((run) => run.portfolio_id === portfolioId);
    },
    enabled: portfolioId !== null,
    retry: 1,
    staleTime: 30_000,
  });
}

export function useOptimizationRun(runId: string | null) {
  return useQuery({
    queryKey: optimizationRunDetailQueryKey(runId),
    queryFn: ({ signal }) => {
      if (runId === null) {
        throw new Error("Optimization run is not available.");
      }

      return fetchOptimizationRun(runId, signal);
    },
    enabled: runId !== null,
    retry: 1,
    staleTime: 2_000,
    refetchInterval: (query) => {
      const run = query.state.data as OptimizationRun | undefined;
      return run?.status === "PENDING" || run?.status === "RUNNING"
        ? 1_000
        : false;
    },
  });
}

export function useCreateOptimizationRun(portfolioId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: OptimizationRunCreateRequest) =>
      createOptimizationRun(request),
    onSuccess: async (run) => {
      queryClient.setQueryData(
        optimizationRunDetailQueryKey(run.id),
        run,
      );

      if (portfolioId !== null) {
        await queryClient.invalidateQueries({
          queryKey: optimizationRunsQueryKey(portfolioId),
        });
      }
    },
  });
}
