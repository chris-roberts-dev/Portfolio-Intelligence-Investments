import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import {
  confirmPortfolioTransactionImport,
  createPortfolio,
  createPortfolioTransaction,
  fetchAssetCatalog,
  fetchDashboardSnapshot,
  fetchPortfolioAnalytics,
  fetchPortfolios,
  previewPortfolioTransactionImport,
  renamePortfolio,
  resolveAssets,
  updatePortfolioBenchmark,
  type DashboardSnapshotRequest,
  type PortfolioAnalyticsRequest,
} from "../api/portfolios";
import type {
  AssetResolveRequest,
  PortfolioBenchmarkRequest,
  PortfolioCreateRequest,
  PortfolioRenameRequest,
  PortfolioTransactionCreateRequest,
  TransactionImportRequest,
} from "../types/portfolioManagement";

export const PORTFOLIOS_QUERY_KEY = ["portfolios"] as const;
export const ASSET_CATALOG_QUERY_KEY = ["asset-catalog"] as const;

async function invalidatePortfolioDerivedQueries(
  queryClient: QueryClient,
  portfolioId: string,
): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: ["portfolio-dashboard", portfolioId],
    }),
    queryClient.invalidateQueries({
      queryKey: ["portfolio-analysis", portfolioId],
    }),
  ]);
}

export function usePortfolios() {
  return useQuery({
    queryKey: PORTFOLIOS_QUERY_KEY,
    queryFn: ({ signal }) => fetchPortfolios(signal),
    staleTime: 30_000,
  });
}

export function useCreatePortfolio() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: PortfolioCreateRequest) => createPortfolio(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: PORTFOLIOS_QUERY_KEY,
      });
    },
  });
}

export function useRenamePortfolio(portfolioId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: PortfolioRenameRequest) =>
      renamePortfolio(portfolioId, request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: PORTFOLIOS_QUERY_KEY,
      });
    },
  });
}

export function useAssetCatalog() {
  return useQuery({
    queryKey: ASSET_CATALOG_QUERY_KEY,
    queryFn: ({ signal }) => fetchAssetCatalog(signal),
    staleTime: 5 * 60 * 1000,
  });
}


export function useResolveAssets() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: AssetResolveRequest) => resolveAssets(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ASSET_CATALOG_QUERY_KEY,
      });
    },
  });
}

export function useUpdatePortfolioBenchmark(portfolioId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: PortfolioBenchmarkRequest) =>
      updatePortfolioBenchmark(portfolioId, request),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: PORTFOLIOS_QUERY_KEY }),
        invalidatePortfolioDerivedQueries(queryClient, portfolioId),
      ]);
    },
  });
}

export function useCreatePortfolioTransaction(portfolioId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: PortfolioTransactionCreateRequest) =>
      createPortfolioTransaction(portfolioId, request),
    onSuccess: async () => {
      await invalidatePortfolioDerivedQueries(queryClient, portfolioId);
    },
  });
}

export function usePreviewPortfolioTransactionImport(portfolioId: string) {
  return useMutation({
    mutationFn: (request: TransactionImportRequest) =>
      previewPortfolioTransactionImport(portfolioId, request),
  });
}

export function useConfirmPortfolioTransactionImport(portfolioId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: TransactionImportRequest) =>
      confirmPortfolioTransactionImport(portfolioId, request),
    onSuccess: async () => {
      await invalidatePortfolioDerivedQueries(queryClient, portfolioId);
    },
  });
}

export function useDashboardSnapshot(
  request: DashboardSnapshotRequest | null,
) {
  return useQuery({
    queryKey:
      request === null
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

export function usePortfolioAnalytics(
  request: PortfolioAnalyticsRequest | null,
) {
  return useQuery({
    queryKey:
      request === null
        ? ["portfolio-analysis", "disabled"]
        : [
            "portfolio-analysis",
            request.portfolioId,
            request.start,
            request.end,
            request.rollingWindow ?? null,
          ],
    queryFn: ({ signal }) => {
      if (request === null) {
        throw new Error("Portfolio analysis request is not available.");
      }

      return fetchPortfolioAnalytics(request, signal);
    },
    enabled: request !== null,
    retry: 1,
    staleTime: 30_000,
  });
}