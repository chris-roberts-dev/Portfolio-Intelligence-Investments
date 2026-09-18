export type RebalanceSchedule = "MONTHLY" | "QUARTERLY" | "ANNUAL";

export interface TargetAllocationWeightRequest {
  asset_id: string | null;
  weight: number;
}

export interface TargetAllocationCreateRequest {
  portfolio_id: string;
  name: string;
  weights: TargetAllocationWeightRequest[];
  source_optimization_run_id?: string | null;
}

export interface TargetAllocationWeight {
  asset_id: string | null;
  is_cash: boolean;
  weight: number;
}

export interface TargetAllocation {
  id: string;
  portfolio_id: string;
  name: string;
  source_optimization_run_id: string | null;
  weights: TargetAllocationWeight[];
  created_at: string;
  updated_at: string;
}

export interface RebalanceSimulationCreateRequest {
  portfolio_id: string;
  target_allocation_id: string;
  drift_threshold?: number;
  schedule?: RebalanceSchedule;
  previous_rebalance_date?: string | null;
}

export type RebalanceTradeDirection = "BUY" | "SELL" | "NONE";

export interface RebalanceLine {
  asset_id: string | null;
  is_cash: boolean;
  current_value: number;
  target_value: number;
  current_weight: number;
  target_weight: number;
  absolute_drift: number;
  relative_drift: number | null;
  trade_notional: number;
  direction: RebalanceTradeDirection;
}

export interface RebalanceRuleResult {
  threshold: number | null;
  threshold_triggered: boolean;
  schedule: RebalanceSchedule | null;
  previous_rebalance_date: string | null;
  decision_date: string;
  schedule_due: boolean;
}

export interface RebalanceSimulationResult {
  total_investable_value: number;
  current_weight_sum: number;
  target_weight_sum: number;
  lines: RebalanceLine[];
  rules: RebalanceRuleResult;
}

export interface RebalancingWarning {
  code: string;
  message: string;
}

export interface RebalanceSimulation {
  id: string;
  portfolio_id: string;
  target_allocation_id: string;
  as_of: string;
  provider: string;
  price_field: string;
  valuation_retrieved_at: string | null;
  drift_threshold: number | null;
  schedule: string;
  previous_rebalance_date: string | null;
  result: RebalanceSimulationResult;
  warnings: RebalancingWarning[];
  created_at: string;
}

export interface HistoricalRebalanceComparisonCreateRequest {
  portfolio_id: string;
  target_allocation_id: string;
  period_start: string;
  period_end: string;
  drift_threshold: number;
  commission_rate?: number;
  slippage_rate?: number;
  include_monthly?: boolean;
}

export interface HistoricalPosition {
  asset_id: string;
  quantity: number;
}

export interface HistoricalTargetWeight {
  asset_id: string | null;
  is_cash: boolean;
  weight: number;
}

export interface HistoricalRebalanceAssumptions {
  price_field: string;
  execution_timing: string;
  commission_rate: number;
  slippage_rate: number;
  turnover_convention: string;
  later_actual_ledger_activity: string;
  actual_portfolio_return_method?: string;
  actual_portfolio_series_basis?: string;
}

export interface HistoricalActualPortfolioPoint {
  trade_date: string;
  portfolio_value: number | null;
  cumulative_return: number;
  growth_of_100?: number;
  // Legacy persisted comparisons may still carry this field.
  comparable_value?: number;
}

export interface HistoricalActualPortfolio {
  available: boolean;
  return_method: string;
  period_start: string | null;
  period_end: string | null;
  starting_portfolio_value: number | null;
  ending_portfolio_value: number | null;
  cumulative_return: number | null;
  growth_of_100_start?: number | null;
  growth_of_100_end?: number | null;
  // Legacy persisted comparisons may still carry these fields.
  comparable_initial_value?: number | null;
  comparable_ending_value?: number | null;
  series: HistoricalActualPortfolioPoint[];
  provenance: {
    provider: string;
    retrieved_at: string | null;
    price_field: string;
  };
  warnings: RebalancingWarning[];
}

export interface HistoricalRebalanceSnapshotLine {
  asset_id: string | null;
  is_cash: boolean;
  market_value: number;
  weight: number;
  target_weight: number;
  absolute_drift: number;
  relative_drift: number | null;
}

export interface HistoricalRebalanceSnapshot {
  trade_date: string;
  total_value: number;
  cash_value: number;
  period_return: number | null;
  growth_of_100?: number;
  lines: HistoricalRebalanceSnapshotLine[];
}

export interface HistoricalRebalanceTrade {
  asset_id: string;
  direction: Exclude<RebalanceTradeDirection, "NONE">;
  quantity: number;
  reference_price: number;
  fill_price: number;
  fill_notional: number;
  commission_cost: number;
  slippage_cost: number;
}

export interface HistoricalRebalanceEvent {
  trigger: string;
  decision_date: string;
  execution_date: string;
  pre_trade_value: number;
  post_trade_value: number;
  turnover: number;
  commission_cost: number;
  slippage_cost: number;
  decision_lines: RebalanceLine[];
  trades: HistoricalRebalanceTrade[];
}

export interface HistoricalRebalancePolicySummary {
  initial_value: number;
  ending_value: number;
  cumulative_return: number;
  growth_of_100_ending?: number;
  return_difference_pp_vs_actual?: number | null;
  rebalance_count: number;
  trade_count: number;
  maximum_absolute_drift: number;
  turnover: number;
  commission_cost: number;
  slippage_cost: number;
  total_cost: number;
}

export interface HistoricalRebalancePolicyResult {
  name: string;
  schedule: RebalanceSchedule | null;
  threshold: number | null;
  summary: HistoricalRebalancePolicySummary;
  snapshots: HistoricalRebalanceSnapshot[];
  events: HistoricalRebalanceEvent[];
  warnings: RebalancingWarning[];
}

export interface HistoricalRebalanceProvenance {
  provider: string;
  retrieved_at: string;
  engine_version: string;
  requested_period_start: string;
  requested_period_end: string;
}

export interface HistoricalRebalanceResult {
  period_start: string;
  period_end: string;
  aligned_dates: string[];
  initial_state: {
    cash: number;
    positions: HistoricalPosition[];
  };
  target_weights: HistoricalTargetWeight[];
  assumptions: HistoricalRebalanceAssumptions;
  actual_portfolio?: HistoricalActualPortfolio | null;
  policies: HistoricalRebalancePolicyResult[];
  provenance: HistoricalRebalanceProvenance;
}

export interface HistoricalRebalanceComparison {
  id: string;
  portfolio_id: string;
  target_allocation_id: string;
  period_start: string;
  period_end: string;
  provider: string;
  price_field: string;
  retrieved_at: string | null;
  drift_threshold: number;
  commission_rate: number;
  slippage_rate: number;
  engine_version: string;
  result: HistoricalRebalanceResult;
  warnings: RebalancingWarning[];
  created_at: string;
}
