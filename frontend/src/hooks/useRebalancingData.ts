import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createHistoricalRebalanceComparison,
  createRebalanceSimulation,
  createTargetAllocation,
  fetchHistoricalRebalanceComparisons,
  fetchRebalanceSimulations,
  fetchTargetAllocations,
} from "../api/rebalancing";
import type {
  HistoricalRebalanceComparisonCreateRequest,
  RebalanceSimulationCreateRequest,
  TargetAllocationCreateRequest,
} from "../types/rebalancing";

export const REBALANCING_ROOT_QUERY_KEY = ["rebalancing"] as const;

export function targetAllocationsQueryKey() {
  return [...REBALANCING_ROOT_QUERY_KEY, "target-allocations"] as const;
}

export function rebalanceSimulationsQueryKey() {
  return [...REBALANCING_ROOT_QUERY_KEY, "simulations"] as const;
}

export function historicalRebalanceComparisonsQueryKey() {
  return [...REBALANCING_ROOT_QUERY_KEY, "historical-comparisons"] as const;
}

export function useTargetAllocations() {
  return useQuery({
    queryKey: targetAllocationsQueryKey(),
    queryFn: ({ signal }) => fetchTargetAllocations(signal),
    retry: 1,
    staleTime: 30_000,
  });
}

export function useCreateTargetAllocation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: TargetAllocationCreateRequest) =>
      createTargetAllocation(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: targetAllocationsQueryKey(),
      });
    },
  });
}

export function useRebalanceSimulations() {
  return useQuery({
    queryKey: rebalanceSimulationsQueryKey(),
    queryFn: ({ signal }) => fetchRebalanceSimulations(signal),
    retry: 1,
    staleTime: 30_000,
  });
}

export function useCreateRebalanceSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: RebalanceSimulationCreateRequest) =>
      createRebalanceSimulation(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: rebalanceSimulationsQueryKey(),
      });
    },
  });
}

export function useHistoricalRebalanceComparisons() {
  return useQuery({
    queryKey: historicalRebalanceComparisonsQueryKey(),
    queryFn: ({ signal }) => fetchHistoricalRebalanceComparisons(signal),
    retry: 1,
    staleTime: 30_000,
  });
}

export function useCreateHistoricalRebalanceComparison() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: HistoricalRebalanceComparisonCreateRequest) =>
      createHistoricalRebalanceComparison(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: historicalRebalanceComparisonsQueryKey(),
      });
    },
  });
}
