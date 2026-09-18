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
  return comparison.result.policies.map((policy) => ({
    name: policy.name,
    points: policy.snapshots.map((snapshot) => [
      snapshot.trade_date,
      snapshot.total_value,
    ]),
  }));
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
