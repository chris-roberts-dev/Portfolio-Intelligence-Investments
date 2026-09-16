export interface EngineWarning {
  code: string;
  message: string;
}

export interface AnnualizedReturnResult {
  value: number;
  wealth_ratio: number;
  elapsed_days: number;
  elapsed_years: number;
  is_short_period: boolean;
}

export interface SharpeRatioResult {
  value: number | null;
  observations: number;
  risk_free_rate_annual: number;
  risk_free_rate_daily: number;
  annualization_factor: number;
  warnings: EngineWarning[];
}

export interface SortinoRatioResult {
  value: number | null;
  observations: number;
  minimum_acceptable_return_annual: number;
  minimum_acceptable_return_daily: number;
  downside_deviation: number | null;
  annualization_factor: number;
  warnings: EngineWarning[];
}

export interface MaximumDrawdownResult {
  value: number | null;
  observations: number;
  peak_index: number | null;
  trough_index: number | null;
  warnings: EngineWarning[];
}

export interface BetaResult {
  value: number | null;
  observations: number;
  warnings: EngineWarning[];
}

export interface CorrelationResult {
  value: number | null;
  observations: number;
  warnings: EngineWarning[];
}

export interface RollingReturnObservation {
  period_end: string;
  value: number;
}

export interface SecurityAllocation {
  asset_id: string;
  market_value: number;
  weight: number;
}

export interface PortfolioAllocationResult {
  positions: SecurityAllocation[];
  cash_value: number;
  cash_weight: number;
  total_market_value: number;
  weight_sum: number;
  weight_sum_tolerance: number;
}

export interface ConcentrationResult {
  largest_position_weight: number | null;
  herfindahl_hirschman_index: number;
  security_position_count: number;
  cash_weight: number;
  largest_position_includes_cash: boolean;
  hhi_includes_cash: boolean;
  long_only: boolean;
  weight_sum_tolerance: number;
}

export interface AnalyticalResultProvenance {
  engine_version: string;
  as_of_date: string;
  period_start: string;
  period_end: string;
  data_source: string;
  price_field: string;
  annualization_factor: number;
  benchmark: string | null;
  assumptions: string[];
  warnings: string[];
}

export type PortfolioAnalyticsWarningCode =
  | "SOURCE_WARNING"
  | "PERFORMANCE_UNAVAILABLE"
  | "INSUFFICIENT_HISTORY"
  | "INSUFFICIENT_ROLLING_HISTORY"
  | "UNDEFINED_CAGR"
  | "UNDEFINED_SHARPE"
  | "UNDEFINED_SORTINO"
  | "BENCHMARK_NOT_CONFIGURED"
  | "BENCHMARK_NOT_FOUND"
  | "BENCHMARK_NO_DATA"
  | "BENCHMARK_PROVIDER_FAILED"
  | "UNDEFINED_BETA"
  | "UNDEFINED_CORRELATION"
  | "CURRENT_VALUATION_INCOMPLETE"
  | "CURRENT_ALLOCATION_UNAVAILABLE";

export interface PortfolioAnalyticsWarning {
  code: PortfolioAnalyticsWarningCode;
  message: string;
  observations: number | null;
}

export interface PortfolioAnalyticsResult {
  portfolio_id: string;
  observations: number;
  benchmark_observations: number | null;
  cumulative_return: number | null;
  cagr: AnnualizedReturnResult | null;
  annualized_volatility: number | null;
  sharpe: SharpeRatioResult | null;
  sortino: SortinoRatioResult | null;
  maximum_drawdown: MaximumDrawdownResult | null;
  beta: BetaResult | null;
  benchmark_correlation: CorrelationResult | null;
  current_allocation: PortfolioAllocationResult | null;
  concentration: ConcentrationResult | null;
  rolling_return_window: number | null;
  rolling_returns: RollingReturnObservation[];
  provenance: AnalyticalResultProvenance;
  warnings: PortfolioAnalyticsWarning[];
}