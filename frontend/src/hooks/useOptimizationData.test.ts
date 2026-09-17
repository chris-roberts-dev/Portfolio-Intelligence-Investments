import {
  optimizationRunDetailQueryKey,
  optimizationRunsQueryKey,
} from "./useOptimizationData";

describe("optimization query keys", () => {
  it("uses one owner-scoped run-history root for standalone Allocation Lab", () => {
    expect(optimizationRunsQueryKey()).toEqual([
      "optimization-runs",
      "owned",
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
