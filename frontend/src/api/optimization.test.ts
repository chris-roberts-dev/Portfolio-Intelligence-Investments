import {
  createOptimizationRun,
  fetchOptimizationRun,
  fetchOptimizationRuns,
} from "./optimization";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "csrftoken=; Max-Age=0; path=/";
});

describe("optimization API", () => {
  it("constructs an ad hoc persisted run with explicit user-controlled configuration", async () => {
    document.cookie = "csrftoken=csrf-token; path=/";
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.method).toBe("POST");
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>;

      expect(body).toEqual({
        source_type: "AD_HOC",
        portfolio_id: null,
        method: "MINIMUM_VARIANCE",
        start: "2025-01-01",
        end: "2026-01-01",
        asset_ids: ["asset-a", "asset-b"],
        bounds: [
          { asset_id: "asset-a", minimum: 0, maximum: 0.7 },
          { asset_id: "asset-b", minimum: 0.3, maximum: 1 },
        ],
        baseline_weights: [
          { asset_id: "asset-a", weight: 0.4 },
          { asset_id: "asset-b", weight: 0.6 },
        ],
        risk_free_rate_annual: 0.03,
      });

      return new Response(
        JSON.stringify({
          id: "run-1",
          source_type: "AD_HOC",
          portfolio_id: null,
          portfolio_name: null,
          status: "SUCCEEDED",
          method: "MINIMUM_VARIANCE",
          included_asset_ids: ["asset-a", "asset-b"],
          baseline_weights: body.baseline_weights,
          parameters: {
            source_type: "AD_HOC",
            requested_asset_ids: ["asset-a", "asset-b"],
            bounds: body.bounds,
            baseline_weights: body.baseline_weights,
            risk_free_rate_annual: 0.03,
            frontier_points: 25,
            observations: 100,
            covariance_rank: 2,
          },
          result: null,
          warnings: [],
          failure_code: "",
          failure_message: "",
          started_at: "2026-09-17T10:00:00Z",
          completed_at: "2026-09-17T10:00:01Z",
          created_at: "2026-09-17T10:00:00Z",
          provenance: {
            period_start: "2025-01-01",
            period_end_exclusive: "2026-01-01",
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
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    await createOptimizationRun({
      source_type: "AD_HOC",
      portfolio_id: null,
      method: "MINIMUM_VARIANCE",
      start: "2025-01-01",
      end: "2026-01-01",
      asset_ids: ["asset-a", "asset-b"],
      bounds: [
        { asset_id: "asset-a", minimum: 0, maximum: 0.7 },
        { asset_id: "asset-b", minimum: 0.3, maximum: 1 },
      ],
      baseline_weights: [
        { asset_id: "asset-a", weight: 0.4 },
        { asset_id: "asset-b", weight: 0.6 },
      ],
      risk_free_rate_annual: 0.03,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/optimization-runs/",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });

  it("uses the global owner-scoped list and detail endpoints", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      return new Response(JSON.stringify(url.includes("run-1") ? { id: "run-1" } : []), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchOptimizationRuns();
    await fetchOptimizationRun("run-1");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/optimization-runs/");
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/v1/optimization-runs/run-1/");
  });
});
