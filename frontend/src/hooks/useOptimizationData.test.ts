import {
  optimizationRunDetailQueryKey,
  optimizationRunsQueryKey,
} from "./useOptimizationData";

describe("optimization query keys", () => {
  it("scopes the run list by portfolio identity", () => {
    expect(optimizationRunsQueryKey("portfolio-1")).toEqual([
      "optimization-runs",
      "portfolio",
      "portfolio-1",
    ]);
  });

  it("scopes persisted run detail by run identity", () => {
    expect(optimizationRunDetailQueryKey("run-1")).toEqual([
      "optimization-runs",
      "detail",
      "run-1",
    ]);
  });
});
