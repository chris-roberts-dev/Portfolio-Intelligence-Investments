import type { OptimizationRun } from "../../types/optimization";
import {
  latestSuccessfulOptimizationRun,
  optimizedWeightForAsset,
  optimizationRunMatchesContext,
} from "./optimizationTransforms";

function run(overrides: Partial<OptimizationRun> = {}): OptimizationRun {
  return {
    id: "run-1",
    portfolio_id: "portfolio-1",
    status: "SUCCEEDED",
    method: "MINIMUM_VARIANCE",
    included_asset_ids: ["asset-a", "asset-b"],
    parameters: {
      requested_asset_ids: ["asset-a", "asset-b"],
      bounds: [
        { asset_id: "asset-a", minimum: 0, maximum: 1 },
        { asset_id: "asset-b", minimum: 0, maximum: 1 },
      ],
      frontier_points: 25,
      observations: 100,
      covariance_rank: 2,
    },
    result: {
      portfolio: {
        method: "MINIMUM_VARIANCE",
        weights: [
          { asset_id: "asset-a", weight: 0.4 },
          { asset_id: "asset-b", weight: 0.6 },
        ],
        expected_return: 0.1,
        expected_volatility: 0.15,
        sharpe_ratio: 0.66,
        target_return: null,
      },
      frontier: [],
    },
    warnings: [],
    failure_code: "",
    failure_message: "",
    started_at: "2026-09-17T10:00:00Z",
    completed_at: "2026-09-17T10:00:01Z",
    created_at: "2026-09-17T10:00:00Z",
    provenance: {
      period_start: "2026-03-17",
      period_end_exclusive: "2026-09-17",
      provider: "yfinance",
      price_field: "adjusted_close",
      annualization_factor: 252,
      risk_free_rate_annual: 0,
      benchmark_asset_id: null,
      engine_version: "0.1.0",
      method_version: "1.0",
      data_retrieved_at: "2026-09-17T10:00:01Z",
      data_fingerprint: "abc",
    },
    ...overrides,
  };
}

const context = {
  start: "2026-03-17",
  end: "2026-09-17",
  assetIds: ["asset-a", "asset-b"],
  bounds: [
    { asset_id: "asset-a", minimum: 0, maximum: 1 },
    { asset_id: "asset-b", minimum: 0, maximum: 1 },
  ],
};

describe("optimization presentation transforms", () => {
  it("matches persisted runs only when period, ordered asset universe, and bounds match", () => {
    expect(optimizationRunMatchesContext(run(), context)).toBe(true);
    expect(
      optimizationRunMatchesContext(
        run({ included_asset_ids: ["asset-b", "asset-a"] }),
        context,
      ),
    ).toBe(false);
    expect(
      optimizationRunMatchesContext(
        run({
          provenance: {
            ...run().provenance,
            period_start: "2026-01-01",
          },
        }),
        context,
      ),
    ).toBe(false);
  });

  it("selects only successful matching method runs in canonical server list order", () => {
    const failed = run({ id: "failed", status: "FAILED" });
    const newest = run({ id: "newest" });
    const older = run({ id: "older" });

    expect(
      latestSuccessfulOptimizationRun(
        [failed, newest, older],
        "MINIMUM_VARIANCE",
        context,
      )?.id,
    ).toBe("newest");
  });

  it("reads authoritative optimized weights without deriving missing values", () => {
    expect(optimizedWeightForAsset(run(), "asset-a")).toBe(0.4);
    expect(optimizedWeightForAsset(run(), "asset-missing")).toBeNull();
    expect(optimizedWeightForAsset(null, "asset-a")).toBeNull();
  });
});
