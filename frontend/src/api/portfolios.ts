import { apiGet, apiPatch, apiPost } from "./client";
import type { PortfolioAnalyticsResult } from "../types/analytics";
import type {
  DashboardSnapshotResult,
  PortfolioListItem,
} from "../types/dashboard";
import type {
  AssetCatalogItem,
  PortfolioBenchmarkRequest,
  PortfolioCreateRequest,
  PortfolioRenameRequest,
  PortfolioTransaction,
  PortfolioTransactionCreateRequest,
  TransactionImportPreview,
  TransactionImportRequest,
  TransactionImportResult,
} from "../types/portfolioManagement";

export interface DashboardSnapshotRequest {
  portfolioId: string;
  start: string;
  end: string;
}

export interface PortfolioAnalyticsRequest {
  portfolioId: string;
  start: string;
  end: string;
  rollingWindow?: number;
}

export function fetchPortfolios(
  signal?: AbortSignal,
): Promise<PortfolioListItem[]> {
  return apiGet<PortfolioListItem[]>("/api/v1/portfolios/", { signal });
}

export function createPortfolio(
  request: PortfolioCreateRequest,
): Promise<PortfolioListItem> {
  return apiPost<PortfolioListItem, PortfolioCreateRequest>(
    "/api/v1/portfolios/",
    request,
  );
}

export function renamePortfolio(
  portfolioId: string,
  request: PortfolioRenameRequest,
): Promise<PortfolioListItem> {
  return apiPatch<PortfolioListItem, PortfolioRenameRequest>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/`,
    request,
  );
}

export function fetchAssetCatalog(
  signal?: AbortSignal,
): Promise<AssetCatalogItem[]> {
  return apiGet<AssetCatalogItem[]>("/api/v1/assets/", { signal });
}

export function updatePortfolioBenchmark(
  portfolioId: string,
  request: PortfolioBenchmarkRequest,
): Promise<PortfolioListItem> {
  return apiPatch<PortfolioListItem, PortfolioBenchmarkRequest>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/benchmark/`,
    request,
  );
}

export function createPortfolioTransaction(
  portfolioId: string,
  request: PortfolioTransactionCreateRequest,
): Promise<PortfolioTransaction> {
  return apiPost<PortfolioTransaction, PortfolioTransactionCreateRequest>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/transactions/`,
    request,
  );
}

export function previewPortfolioTransactionImport(
  portfolioId: string,
  request: TransactionImportRequest,
): Promise<TransactionImportPreview> {
  return apiPost<TransactionImportPreview, TransactionImportRequest>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/transactions/import/preview/`,
    request,
  );
}

export function confirmPortfolioTransactionImport(
  portfolioId: string,
  request: TransactionImportRequest,
): Promise<TransactionImportResult> {
  return apiPost<TransactionImportResult, TransactionImportRequest>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/transactions/import/confirm/`,
    request,
  );
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

export function fetchPortfolioAnalytics(
  request: PortfolioAnalyticsRequest,
  signal?: AbortSignal,
): Promise<PortfolioAnalyticsResult> {
  const params = new URLSearchParams({
    start: request.start,
    end: request.end,
  });

  if (request.rollingWindow !== undefined) {
    params.set("rolling_window", String(request.rollingWindow));
  }

  const portfolioId = encodeURIComponent(request.portfolioId);

  return apiGet<PortfolioAnalyticsResult>(
    `/api/v1/analytics/portfolios/${portfolioId}/?${params.toString()}`,
    { signal },
  );
}
