import type { OptimizationRun } from "../../types/optimization";
import type { HistoricalRebalanceComparison, TargetAllocation } from "../../types/rebalancing";
import {
  historicalValueChartSeries,
  successfulPortfolioOptimizationRuns,
  targetAllocationsForPortfolio,
  targetRequestFromOptimizationRun,
  tradeLines,
} from "./rebalancingTransforms";

const RUN: OptimizationRun = {
  id: "run-1",
  source_type: "PORTFOLIO",
  portfolio_id: "portfolio-1",
  portfolio_name: "Primary",
  status: "SUCCEEDED",
  method: "MINIMUM_VARIANCE",
  included_asset_ids: ["asset-a", "asset-b"],
  baseline_weights: [],
  parameters: {
    source_type: "PORTFOLIO",
    requested_asset_ids: null,
    bounds: [],
    baseline_weights: [],
    risk_free_rate_annual: 0,
    frontier_points: 25,
  },
  result: {
    portfolio: {
      method: "MINIMUM_VARIANCE",
      weights: [
        { asset_id: "asset-a", weight: 0.6 },
        { asset_id: "asset-b", weight: 0.4 },
      ],
      expected_return: 0.1,
      expected_volatility: 0.2,
      sharpe_ratio: 0.5,
      target_return: null,
    },
    frontier: [],
  },
  warnings: [],
  failure_code: "",
  failure_message: "",
  started_at: "2026-09-17T12:00:00Z",
  completed_at: "2026-09-17T12:00:01Z",
  created_at: "2026-09-17T12:00:00Z",
  provenance: {
    period_start: "2026-01-01",
    period_end_exclusive: "2026-09-01",
    provider: "csv",
    price_field: "adjusted_close",
    annualization_factor: 252,
    risk_free_rate_annual: 0,
    benchmark_asset_id: null,
    engine_version: "0.1.0.dev0",
    method_version: "1",
    data_retrieved_at: "2026-09-17T12:00:00Z",
    data_fingerprint: "fixture",
  },
};

function comparisonFixture(): HistoricalRebalanceComparison {
  const policy = (name: string, values: number[]) => ({
    name,
    schedule: name === "threshold" ? null : (name.toUpperCase() as "ANNUAL" | "QUARTERLY"),
    threshold: name === "threshold" ? 0.05 : null,
    summary: {
      initial_value: 100,
      ending_value: values.at(-1) ?? 100,
      cumulative_return: 0.1,
      rebalance_count: 1,
      trade_count: 2,
      maximum_absolute_drift: 0.07,
      turnover: 0.2,
      commission_cost: 1,
      slippage_cost: 2,
      total_cost: 3,
    },
    snapshots: [
      { trade_date: "2026-01-02", total_value: values[0] ?? 100, cash_value: 0, period_return: null, growth_of_100: values[0] ?? 100, lines: [] },
      { trade_date: "2026-01-05", total_value: values[1] ?? 101, cash_value: 0, period_return: 0.01, growth_of_100: values[1] ?? 101, lines: [] },
    ],
    events: [],
    warnings: [],
  });

  return {
    id: "comparison-1",
    portfolio_id: "portfolio-1",
    target_allocation_id: "target-1",
    period_start: "2026-01-02",
    period_end: "2026-01-05",
    provider: "csv",
    price_field: "adjusted_close",
    retrieved_at: "2026-01-05T23:00:00Z",
    drift_threshold: 0.05,
    commission_rate: 0,
    slippage_rate: 0,
    engine_version: "0.1.0.dev0",
    warnings: [],
    created_at: "2026-01-06T00:00:00Z",
    result: {
      period_start: "2026-01-02",
      period_end: "2026-01-05",
      aligned_dates: ["2026-01-02", "2026-01-05"],
      initial_state: { cash: 0, positions: [] },
      target_weights: [],
      assumptions: {
        price_field: "adjusted_close",
        execution_timing: "decision_at_t_execute_at_next_aligned_observation",
        commission_rate: 0,
        slippage_rate: 0,
        turnover_convention: "persisted backend convention",
        later_actual_ledger_activity: "ignored_by_hypothetical_policies",
        actual_portfolio_return_method: "TIME_WEIGHTED",
        actual_portfolio_series_basis: "normalized_growth_of_100_from_same_period_twr",
      },
      actual_portfolio: {
        available: true,
        return_method: "TIME_WEIGHTED",
        period_start: "2026-01-02",
        period_end: "2026-01-05",
        starting_portfolio_value: 100,
        ending_portfolio_value: 100.5,
        cumulative_return: 0.005,
        growth_of_100_start: 100,
        growth_of_100_end: 100.5,
        series: [
          { trade_date: "2026-01-02", portfolio_value: 100, cumulative_return: 0, growth_of_100: 100 },
          { trade_date: "2026-01-05", portfolio_value: 100.5, cumulative_return: 0.005, growth_of_100: 100.5 },
        ],
        provenance: { provider: "csv", retrieved_at: "2026-01-05T23:00:00Z", price_field: "adjusted_close" },
        warnings: [],
      },
      policies: [policy("annual", [100, 101]), policy("quarterly", [100, 102]), policy("threshold", [100, 103])],
      provenance: {
        provider: "csv",
        retrieved_at: "2026-01-05T23:00:00Z",
        engine_version: "0.1.0.dev0",
        requested_period_start: "2026-01-01",
        requested_period_end: "2026-01-05",
      },
    },
  };
}

describe("rebalancing presentation transforms", () => {
  it("filters owned targets and successful portfolio-derived optimization runs", () => {
    const targets = [
      { id: "a", portfolio_id: "portfolio-1" },
      { id: "b", portfolio_id: "portfolio-2" },
    ] as TargetAllocation[];

    expect(targetAllocationsForPortfolio(targets, "portfolio-1").map((item) => item.id)).toEqual(["a"]);
    expect(successfulPortfolioOptimizationRuns([RUN], "portfolio-1")).toEqual([RUN]);
    expect(successfulPortfolioOptimizationRuns([{ ...RUN, status: "FAILED" }], "portfolio-1")).toEqual([]);
  });

  it("maps a successful optimization portfolio to a target request without changing weights", () => {
    expect(targetRequestFromOptimizationRun(RUN, "  Saved target  ")).toEqual({
      portfolio_id: "portfolio-1",
      name: "Saved target",
      source_optimization_run_id: "run-1",
      weights: [
        { asset_id: "asset-a", weight: 0.6 },
        { asset_id: "asset-b", weight: 0.4 },
      ],
    });
  });

  it("treats cash movement as state adjustment rather than a security trade", () => {
    expect(
      tradeLines([
        {
          asset_id: "asset-a",
          is_cash: false,
          current_value: 60,
          target_value: 50,
          current_weight: 0.6,
          target_weight: 0.5,
          absolute_drift: 0.1,
          relative_drift: 0.2,
          trade_notional: -10,
          direction: "SELL",
        },
        {
          asset_id: null,
          is_cash: true,
          current_value: 40,
          target_value: 50,
          current_weight: 0.4,
          target_weight: 0.5,
          absolute_drift: -0.1,
          relative_drift: -0.2,
          trade_notional: 10,
          direction: "BUY",
        },
      ]).map((line) => line.asset_id),
    ).toEqual(["asset-a"]);
  });

  it("reshapes persisted snapshot values for charts without recomputing performance", () => {
    expect(historicalValueChartSeries(comparisonFixture())).toEqual([
      { name: "actual", points: [["2026-01-02", 100], ["2026-01-05", 100.5]] },
      { name: "annual", points: [["2026-01-02", 100], ["2026-01-05", 101]] },
      { name: "quarterly", points: [["2026-01-02", 100], ["2026-01-05", 102]] },
      { name: "threshold", points: [["2026-01-02", 100], ["2026-01-05", 103]] },
    ]);
  });
});
