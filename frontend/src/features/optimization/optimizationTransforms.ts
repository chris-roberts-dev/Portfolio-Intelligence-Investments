import type {
  OptimizationRun,
  OptimizationRunMethod,
  OptimizationWeightBoundRequest,
} from "../../types/optimization";

export interface OptimizationControlContext {
  start: string;
  end: string;
  assetIds: string[];
  bounds: OptimizationWeightBoundRequest[];
}

function sameStringArray(left: readonly string[], right: readonly string[]): boolean {
  return (
    left.length === right.length &&
    left.every((value, index) => value === right[index])
  );
}

function sameBounds(
  left: readonly OptimizationWeightBoundRequest[],
  right: readonly OptimizationWeightBoundRequest[],
): boolean {
  if (left.length !== right.length) {
    return false;
  }

  const rightByAsset = new Map(
    right.map((bound) => [bound.asset_id, bound] as const),
  );

  return left.every((bound) => {
    const candidate = rightByAsset.get(bound.asset_id);
    return (
      candidate !== undefined &&
      candidate.minimum === bound.minimum &&
      candidate.maximum === bound.maximum
    );
  });
}

export function optimizationRunMatchesContext(
  run: OptimizationRun,
  context: OptimizationControlContext,
): boolean {
  return (
    run.provenance.period_start === context.start &&
    run.provenance.period_end_exclusive === context.end &&
    sameStringArray(run.included_asset_ids, context.assetIds) &&
    sameBounds(run.parameters.bounds ?? [], context.bounds)
  );
}

export function latestSuccessfulOptimizationRun(
  runs: readonly OptimizationRun[],
  method: OptimizationRunMethod,
  context: OptimizationControlContext,
): OptimizationRun | null {
  return (
    runs.find(
      (run) =>
        run.status === "SUCCEEDED" &&
        run.method === method &&
        optimizationRunMatchesContext(run, context),
    ) ?? null
  );
}

export function optimizedWeightForAsset(
  run: OptimizationRun | null,
  assetId: string,
): number | null {
  if (run?.status !== "SUCCEEDED" || run.result?.portfolio == null) {
    return null;
  }

  return (
    run.result.portfolio.weights.find(
      (weight) => weight.asset_id === assetId,
    )?.weight ?? null
  );
}
