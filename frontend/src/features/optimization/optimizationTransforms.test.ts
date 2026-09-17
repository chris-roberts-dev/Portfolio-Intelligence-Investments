import type { OptimizationRun } from "../../types/optimization";
import {
  latestSuccessfulOptimizationRun,
  optimizationRunMatchesContext,
  optimizedWeightForAsset,
} from "./optimizationTransforms";

function run(overrides: Partial<OptimizationRun> = {}): OptimizationRun {
  return {
    id: "run-1",
    source_type: "AD_HOC",
    portfolio_id: null,
    portfolio_name: null,
    status: "SUCCEEDED",
    method: "MINIMUM_VARIANCE",
    included_asset_ids: ["asset-a", "asset-b"],
    baseline_weights: [],
    parameters: {
      source_type: "AD_HOC",
      requested_asset_ids: ["asset-a", "asset-b"],
      bounds: [
        { asset_id: "asset-a", minimum: 0, maximum: 1 },
        { asset_id: "asset-b", minimum: 0, maximum: 1 },
      ],
      baseline_weights: [],
      risk_free_rate_annual: 0.03,
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
      risk_free_rate_annual: 0.03,
      benchmark_asset_id: null,
      engine_version: "0.2.0",
      method_version: "1.0",
      data_retrieved_at: "2026-09-17T10:00:01Z",
      data_fingerprint: "abc",
    },
    ...overrides,
  };
}

const context = {
  sourceType: "AD_HOC" as const,
  portfolioId: null,
  start: "2026-03-17",
  end: "2026-09-17",
  assetIds: ["asset-a", "asset-b"],
  bounds: [
    { asset_id: "asset-a", minimum: 0, maximum: 1 },
    { asset_id: "asset-b", minimum: 0, maximum: 1 },
  ],
  riskFreeRateAnnual: 0.03,
};

describe("optimization presentation transforms", () => {
  it("matches only identical source, period, asset universe, bounds, and risk-free rate", () => {
    expect(optimizationRunMatchesContext(run(), context)).toBe(true);
    expect(
      optimizationRunMatchesContext(
        run({ included_asset_ids: ["asset-b", "asset-a"] }),
        context,
      ),
    ).toBe(false);
    expect(
      optimizationRunMatchesContext(
        run({ source_type: "PORTFOLIO", portfolio_id: "portfolio-1" }),
        context,
      ),
    ).toBe(false);
    expect(
      optimizationRunMatchesContext(
        run({
          provenance: {
            ...run().provenance,
            risk_free_rate_annual: 0,
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
