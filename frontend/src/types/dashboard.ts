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

export type DashboardAllocationUnavailableReason =
  | "CURRENT_VALUATION_INCOMPLETE"
  | "CURRENT_ALLOCATION_UNAVAILABLE";

export interface DashboardAllocationGroup {
  key: string;
  label: string;
  is_cash: boolean;
  asset_count: number;
  market_value: string;
  weight: number | null;
}

export interface DashboardAllocationTotals {
  total_market_value: string | null;
  invested_value: string | null;
  cash_value: string;
  invested_weight: number | null;
  cash_weight: number | null;
}

export interface DashboardAllocationProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  as_of: string;
  data_as_of: string | null;
  calculated_at: string;
  price_field: string;
  grouping_dimension: string;
  supported_grouping_dimensions: string[];
  grouping_source: string;
  ordering_rule: string;
  other_grouping_applied: boolean;
  other_grouping_threshold: number | null;
  other_grouping_rule: string;
  weight_sum_tolerance: number;
}

export interface DashboardAllocationResult {
  allocation_available: boolean;
  groups: DashboardAllocationGroup[];
  totals: DashboardAllocationTotals;
  data_quality: PerformanceDataQuality;
  unavailable_reason: DashboardAllocationUnavailableReason | null;
  warnings: string[];
  provenance: DashboardAllocationProvenance;
}

export interface AllocationGroupSelection {
  grouping_dimension: string;
  group_key: string;
}

export type HoldingMetricUnavailableReason =
  | "CURRENT_PRICE_UNAVAILABLE"
  | "PERIOD_HISTORY_UNAVAILABLE"
  | "PERIOD_START_PRICE_UNAVAILABLE"
  | "PERIOD_END_PRICE_UNAVAILABLE"
  | "CURRENT_ALLOCATION_UNAVAILABLE"
  | "CONTRIBUTION_NOT_CALCULATED";

export interface HoldingSparklinePoint {
  observation_date: string;
  adjusted_close: string | null;
}

export interface DashboardHoldingWarning {
  code: string;
  message: string;
  asset_id: string;
  symbol: string;
  observation_date: string | null;
}

export interface DashboardHolding {
  asset_id: string;
  symbol: string;
  name: string;
  asset_type: string;
  currency: string;
  quantity: string;
  current_price: string | null;
  current_price_date: string | null;
  current_price_retrieved_at: string | null;
  stale_trading_sessions: number | null;
  market_value: string | null;
  weight: number | null;
  weight_unavailable_reason: HoldingMetricUnavailableReason | null;
  selected_period_return: number | null;
  selected_period_return_unavailable_reason: HoldingMetricUnavailableReason | null;
  contribution_to_return: number | null;
  contribution_unavailable_reason: HoldingMetricUnavailableReason | null;
  sparkline: HoldingSparklinePoint[];
  data_quality: PerformanceDataQuality;
  warnings: DashboardHoldingWarning[];
}

export interface DashboardHoldingsProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  current_price_as_of: string | null;
  period_data_as_of: string | null;
  calculated_at: string;
  current_price_field: string;
  period_price_field: string;
}

export interface DashboardHoldingsResult {
  holdings: DashboardHolding[];
  data_quality: PerformanceDataQuality;
  warnings: DashboardHoldingWarning[];
  provenance: DashboardHoldingsProvenance;
}

export type MoversAttributionStatus = "AVAILABLE" | "UNAVAILABLE";

export type MoversAttributionUnavailableReason =
  | "PORTFOLIO_TWR_UNAVAILABLE";

export type MoverUnavailableReason =
  | "NOT_CURRENT_HOLDING"
  | "SELECTED_PERIOD_RETURN_UNAVAILABLE"
  | "CONTRIBUTION_UNAVAILABLE";

export interface DashboardMover {
  asset_id: string;
  symbol: string;
  name: string;
  asset_type: string;
  currency: string;
  is_current_holding: boolean;
  quantity: string | null;
  current_price: string | null;
  current_price_date: string | null;
  current_price_retrieved_at: string | null;
  stale_trading_sessions: number | null;
  market_value: string | null;
  weight: number | null;
  selected_period_return: number | null;
  contribution_to_return: number | null;
  sparkline: HoldingSparklinePoint[];
  data_quality: PerformanceDataQuality;
  unavailable_reasons: MoverUnavailableReason[];
}

export interface MoversReconciliation {
  status: MoversAttributionStatus;
  periods: number;
  cumulative_return: number | null;
  asset_contribution_total: number | null;
  unattributed_contribution: number | null;
  reconciliation_error: number | null;
  unavailable_reason: MoversAttributionUnavailableReason | null;
}

export interface DashboardMoversProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  current_price_as_of: string | null;
  period_data_as_of: string | null;
  calculated_at: string;
  current_price_field: string;
  period_price_field: string;
  attribution_method: string;
  engine_version: string;
}

export interface DashboardMoversResult {
  top_gainers: DashboardMover[];
  top_losers: DashboardMover[];
  largest_contributors: DashboardMover[];
  largest_detractors: DashboardMover[];
  reconciliation: MoversReconciliation;
  data_quality: PerformanceDataQuality;
  warnings: string[];
  provenance: DashboardMoversProvenance;
}

export interface DashboardSnapshotResult {
  snapshot: DashboardSnapshotContext;
  is_complete: boolean;
  modules: DashboardSnapshotModuleState[];
  summary: DashboardPortfolioSummaryResult | null;
  performance: DashboardPerformanceResult | null;
  allocation: DashboardAllocationResult | null;
  holdings: DashboardHoldingsResult | null;
  movers: DashboardMoversResult | null;
  analytics: unknown | null;
  review_items: DashboardReviewItemsResult | null;
}

export type ReviewItemSeverity = "ERROR" | "WARNING" | "INFO";

export type ReviewItemCategory =
  | "MARKET_DATA"
  | "DATA_COVERAGE"
  | "PROVIDER"
  | "VALUATION"
  | "ANALYTICS";

export type ReviewItemSource =
  | "CURRENT_VALUATION"
  | "DAILY_PERFORMANCE"
  | "ANALYTICS";

export type ReviewDrilldownResource =
  | "HOLDINGS"
  | "PERFORMANCE"
  | "ANALYTICS";

export interface DashboardReviewDrilldown {
  resource: ReviewDrilldownResource;
  portfolio_id: string;
  requested_start: string;
  requested_end_exclusive: string;
  asset_id: string | null;
  symbol: string | null;
  observation_date: string | null;
}

export interface DashboardReviewItem {
  key: string;
  source: ReviewItemSource;
  severity: ReviewItemSeverity;
  category: ReviewItemCategory;
  code: string;
  message: string;
  drilldown: DashboardReviewDrilldown;
}

export interface DashboardReviewCount<TKey extends string = string> {
  key: TKey;
  count: number;
}

export interface DashboardReviewCounts {
  total: number;
  by_severity: DashboardReviewCount<ReviewItemSeverity>[];
  by_category: DashboardReviewCount<ReviewItemCategory>[];
}

export interface DashboardReviewFilters {
  severity: ReviewItemSeverity | null;
  category: ReviewItemCategory | null;
}

export interface DashboardReviewProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  current_data_as_of: string | null;
  historical_data_as_of: string | null;
  analytics_as_of_date: string;
  calculated_at: string;
  engine_version: string;
  included_sources: ReviewItemSource[];
  ordering_rule: string;
}

export interface DashboardReviewItemsResult {
  counts: DashboardReviewCounts;
  filtered_count: number;
  filters: DashboardReviewFilters;
  items: DashboardReviewItem[];
  provenance: DashboardReviewProvenance;
}