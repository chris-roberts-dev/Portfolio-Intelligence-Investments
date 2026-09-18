import {
  createHistoricalRebalanceComparison,
  createRebalanceSimulation,
  createTargetAllocation,
  fetchHistoricalRebalanceComparisons,
  fetchRebalanceSimulations,
  fetchTargetAllocations,
} from "./rebalancing";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("rebalancing API", () => {
  it("uses the canonical Phase 5 resource paths for owned rebalancing data", async () => {
    const fetchMock = vi.fn(async () => jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await fetchTargetAllocations();
    await fetchRebalanceSimulations();
    await fetchHistoricalRebalanceComparisons();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/target-allocations/",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/rebalance-simulations/",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/v1/historical-rebalance-comparisons/",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
  });

  it("posts target, current simulation, and historical comparison inputs without financial transformation", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/target-allocations/")) {
        return jsonResponse({ id: "target-1" }, 201);
      }
      if (url.endsWith("/rebalance-simulations/")) {
        return jsonResponse({ id: "simulation-1" }, 201);
      }
      return jsonResponse({ id: "comparison-1" }, 201);
    });
    vi.stubGlobal("fetch", fetchMock);

    await createTargetAllocation({
      portfolio_id: "portfolio-1",
      name: "Minimum variance target",
      source_optimization_run_id: "run-1",
      weights: [
        { asset_id: "asset-a", weight: 0.6 },
        { asset_id: "asset-b", weight: 0.4 },
      ],
    });
    await createRebalanceSimulation({
      portfolio_id: "portfolio-1",
      target_allocation_id: "target-1",
      drift_threshold: 0.05,
    });
    await createHistoricalRebalanceComparison({
      portfolio_id: "portfolio-1",
      target_allocation_id: "target-1",
      period_start: "2026-02-02",
      period_end: "2026-09-15",
      drift_threshold: 0.05,
      commission_rate: 0.001,
      slippage_rate: 0.002,
      include_monthly: false,
    });

    const targetInit = fetchMock.mock.calls[0]?.[1];
    expect(targetInit).toBeDefined();
    expect(JSON.parse(String(targetInit?.body))).toEqual({
      portfolio_id: "portfolio-1",
      name: "Minimum variance target",
      source_optimization_run_id: "run-1",
      weights: [
        { asset_id: "asset-a", weight: 0.6 },
        { asset_id: "asset-b", weight: 0.4 },
      ],
    });

    const simulationInit = fetchMock.mock.calls[1]?.[1];
    expect(simulationInit).toBeDefined();
    expect(JSON.parse(String(simulationInit?.body))).toEqual({
      portfolio_id: "portfolio-1",
      target_allocation_id: "target-1",
      drift_threshold: 0.05,
    });

    const comparisonInit = fetchMock.mock.calls[2]?.[1];
    expect(comparisonInit).toBeDefined();
    expect(JSON.parse(String(comparisonInit?.body))).toEqual({
      portfolio_id: "portfolio-1",
      target_allocation_id: "target-1",
      period_start: "2026-02-02",
      period_end: "2026-09-15",
      drift_threshold: 0.05,
      commission_rate: 0.001,
      slippage_rate: 0.002,
      include_monthly: false,
    });
  });
});
