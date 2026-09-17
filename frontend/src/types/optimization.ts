export type OptimizationRunStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED";

export type OptimizationRunMethod =
  | "EQUAL_WEIGHT"
  | "MINIMUM_VARIANCE"
  | "MAXIMUM_SHARPE"
  | "EFFICIENT_FRONTIER";

export interface OptimizationWeightBoundRequest {
  asset_id: string;
  minimum: number;
  maximum: number;
}

export interface OptimizationRunCreateRequest {
  portfolio_id: string;
  method: OptimizationRunMethod;
  start: string;
  end: string;
  asset_ids?: string[];
  bounds?: OptimizationWeightBoundRequest[];
  frontier_points?: number;
}

export interface OptimizationWeight {
  asset_id: string;
  weight: number;
}

export interface OptimizedPortfolioResult {
  method: OptimizationRunMethod;
  weights: OptimizationWeight[];
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number | null;
  target_return: number | null;
}

export interface OptimizationResult {
  portfolio: OptimizedPortfolioResult | null;
  frontier: OptimizedPortfolioResult[];
}

export interface OptimizationRunWarning {
  code: string;
  message: string;
}

export interface OptimizationRunParameters {
  requested_asset_ids: string[] | null;
  bounds: OptimizationWeightBoundRequest[];
  frontier_points: number;
  observations?: number;
  covariance_rank?: number;
}

export interface OptimizationRunProvenance {
  period_start: string;
  period_end_exclusive: string;
  provider: string;
  price_field: string;
  annualization_factor: number;
  risk_free_rate_annual: number;
  benchmark_asset_id: string | null;
  engine_version: string;
  method_version: string;
  data_retrieved_at: string | null;
  data_fingerprint: string;
}

export interface OptimizationRun {
  id: string;
  portfolio_id: string;
  status: OptimizationRunStatus;
  method: OptimizationRunMethod;
  included_asset_ids: string[];
  parameters: OptimizationRunParameters;
  result: OptimizationResult | null;
  warnings: OptimizationRunWarning[];
  failure_code: string;
  failure_message: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  provenance: OptimizationRunProvenance;
}
