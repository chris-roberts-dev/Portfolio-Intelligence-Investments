import type { OptimizationRun } from "../../types/optimization";
import type {
  HistoricalRebalanceComparison,
  HistoricalRebalancePolicyResult,
  RebalanceLine,
  TargetAllocation,
  TargetAllocationCreateRequest,
} from "../../types/rebalancing";

export interface RebalanceValueChartSeries {
  name: string;
  points: Array<[string, number]>;
}

export function targetAllocationsForPortfolio(
  targets: readonly TargetAllocation[],
  portfolioId: string,
): TargetAllocation[] {
  return targets.filter((target) => target.portfolio_id === portfolioId);
}

export function successfulPortfolioOptimizationRuns(
  runs: readonly OptimizationRun[],
  portfolioId: string,
): OptimizationRun[] {
  return runs.filter(
    (run) =>
      run.source_type === "PORTFOLIO" &&
      run.portfolio_id === portfolioId &&
      run.status === "SUCCEEDED" &&
      run.result?.portfolio !== null &&
      run.result?.portfolio !== undefined,
  );
}

export function targetRequestFromOptimizationRun(
  run: OptimizationRun,
  name: string,
): TargetAllocationCreateRequest | null {
  if (
    run.source_type !== "PORTFOLIO" ||
    run.portfolio_id === null ||
    run.status !== "SUCCEEDED" ||
    run.result?.portfolio === null ||
    run.result?.portfolio === undefined
  ) {
    return null;
  }

  return {
    portfolio_id: run.portfolio_id,
    name: name.trim(),
    source_optimization_run_id: run.id,
    weights: run.result.portfolio.weights.map((weight) => ({
      asset_id: weight.asset_id,
      weight: weight.weight,
    })),
  };
}

export function tradeLines(lines: readonly RebalanceLine[]): RebalanceLine[] {
  return lines.filter(
    (line) =>
      !line.is_cash &&
      line.direction !== "NONE" &&
      Math.abs(line.trade_notional) > 0,
  );
}

export function historicalValueChartSeries(
  comparison: HistoricalRebalanceComparison,
): RebalanceValueChartSeries[] {
  const policySeries = comparison.result.policies.map((policy) => ({
    name: policy.name,
    points: policy.snapshots.map((snapshot) => [
      snapshot.trade_date,
      snapshot.growth_of_100 ??
        (policy.summary.initial_value > 0
          ? (100 * snapshot.total_value) / policy.summary.initial_value
          : 100),
    ] as [string, number]),
  }));
  const actual = comparison.result.actual_portfolio;

  if (!actual?.available || actual.series.length === 0) {
    return policySeries;
  }

  return [
    {
      name: "actual",
      points: actual.series.map((point) => [
        point.trade_date,
        point.growth_of_100 ?? legacyActualGrowthOf100(actual, point.comparable_value),
      ] as [string, number]),
    },
    ...policySeries,
  ];
}

function legacyActualGrowthOf100(
  actual: HistoricalRebalanceComparison["result"]["actual_portfolio"],
  comparableValue: number | undefined,
): number {
  if (
    actual === undefined ||
    actual === null ||
    comparableValue === undefined ||
    actual.comparable_initial_value === undefined ||
    actual.comparable_initial_value === null ||
    actual.comparable_initial_value <= 0
  ) {
    return 100;
  }

  return (100 * comparableValue) / actual.comparable_initial_value;
}

export function policyByName(
  comparison: HistoricalRebalanceComparison | null,
  policyName: string,
): HistoricalRebalancePolicyResult | null {
  if (comparison === null) {
    return null;
  }
  return (
    comparison.result.policies.find((policy) => policy.name === policyName) ??
    comparison.result.policies[0] ??
    null
  );
}
