export type PerformanceDataQuality =
  | "CURRENT"
  | "STALE"
  | "PARTIAL"
  | "UNAVAILABLE";

export type DashboardSnapshotModule =
  | "SUMMARY"
  | "PERFORMANCE"
  | "ALLOCATION"
  | "HOLDINGS"
  | "MOVERS"
  | "ANALYTICS"
  | "REVIEW_ITEMS";

export type DashboardSnapshotModuleStatus = "AVAILABLE" | "UNAVAILABLE";

export interface PortfolioListItem {
  id: string;
  name: string;
  base_currency: string;
  benchmark_asset_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardSnapshotModuleState {
  module: DashboardSnapshotModule;
  status: DashboardSnapshotModuleStatus;
  error_code: string | null;
  detail: string | null;
}

export interface DashboardSnapshotContext {
  snapshot_id: string;
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  valuation_cutoff: string;
  calculated_at: string;
  engine_version: string;
  current_data_as_of: string | null;
  historical_data_as_of: string | null;
  analytics_as_of_date: string | null;
}

export interface PortfolioPerformanceSummary {
  starting_value: string | null;
  ending_value: string | null;
  value_change: string | null;
  net_external_flow: string;
  investment_gain_loss: string | null;
  cumulative_return: number | null;
  benchmark_cumulative_return: number | null;
}

export interface PortfolioPerformancePoint {
  observation_date: string;
  portfolio_value: string | null;
  net_external_flow: string;
  daily_return: number | null;
  cumulative_return: number | null;
  data_quality: PerformanceDataQuality;
  warnings: string[];
}

export interface BenchmarkPerformancePoint {
  observation_date: string;
  adjusted_close: string | null;
  cumulative_return: number | null;
  data_quality: PerformanceDataQuality;
}

export interface DashboardPerformanceWarning {
  code: string;
  message: string;
  observation_date: string | null;
  asset_id: string | null;
  symbol: string | null;
}

export interface DashboardPerformanceProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  data_as_of: string | null;
  calculated_at: string;
  engine_version: string;
  price_field: string;
  benchmark_asset_id: string | null;
  benchmark_symbol: string | null;
}

export interface DashboardPerformanceResult {
  summary: PortfolioPerformanceSummary;
  points: PortfolioPerformancePoint[];
  benchmark_points: BenchmarkPerformancePoint[];
  portfolio_data_quality: PerformanceDataQuality;
  benchmark_data_quality: PerformanceDataQuality | null;
  warnings: DashboardPerformanceWarning[];
  provenance: DashboardPerformanceProvenance;
}

export type PortfolioSummaryUnavailableReason =
  | "CURRENT_VALUATION_INCOMPLETE"
  | "TOTAL_MARKET_VALUE_NON_POSITIVE"
  | "SELECTED_PERIOD_NOT_STARTED";

export interface DashboardPortfolioSummaryMetrics {
  total_market_value: string | null;
  total_market_value_unavailable_reason: PortfolioSummaryUnavailableReason | null;
  net_contributions: string;
  cost_basis: string;
  cash_balance: string;
  cash_percentage: string | null;
  cash_percentage_unavailable_reason: PortfolioSummaryUnavailableReason | null;
  unrealized_gain_loss: string | null;
  unrealized_gain_loss_unavailable_reason: PortfolioSummaryUnavailableReason | null;
  selected_period_realized_gain_loss: string | null;
  selected_period_realized_gain_loss_unavailable_reason:
    | PortfolioSummaryUnavailableReason
    | null;
  selected_period_income_received: string | null;
  selected_period_income_unavailable_reason: PortfolioSummaryUnavailableReason | null;
}

export interface DashboardPortfolioSummaryProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  ledger_as_of: string;
  current_price_data_as_of: string | null;
  calculated_at: string;
  current_price_field: string;
  accounting_method: string;
  accounting_assumptions: string[];
  selected_period_transaction_timezone: string;
  net_contributions_scope: string;
  selected_period_accounting_scope: string;
}

export interface DashboardPortfolioSummaryResult {
  metrics: DashboardPortfolioSummaryMetrics;
  data_quality: PerformanceDataQuality;
  warnings: string[];
  provenance: DashboardPortfolioSummaryProvenance;
}

export interface DashboardSnapshotResult {
  snapshot: DashboardSnapshotContext;
  is_complete: boolean;
  modules: DashboardSnapshotModuleState[];
  summary: DashboardPortfolioSummaryResult | null;
  performance: DashboardPerformanceResult | null;
  allocation: unknown | null;
  holdings: unknown | null;
  movers: unknown | null;
  analytics: unknown | null;
  review_items: unknown | null;
}
