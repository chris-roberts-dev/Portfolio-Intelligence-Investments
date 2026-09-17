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
  it("constructs the persisted optimization-run request without a frontend risk-free-rate assumption", async () => {
    document.cookie = "csrftoken=csrf-token; path=/";
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.method).toBe("POST");
      const body = JSON.parse(String(init?.body)) as Record<string, unknown>;

      expect(body).toEqual({
        portfolio_id: "portfolio-1",
        method: "MINIMUM_VARIANCE",
        start: "2026-03-17",
        end: "2026-09-17",
        asset_ids: ["asset-a", "asset-b"],
        bounds: [
          { asset_id: "asset-a", minimum: 0, maximum: 0.7 },
          { asset_id: "asset-b", minimum: 0.3, maximum: 1 },
        ],
      });
      expect(body).not.toHaveProperty("risk_free_rate_annual");

      return new Response(
        JSON.stringify({
          id: "run-1",
          portfolio_id: "portfolio-1",
          status: "SUCCEEDED",
          method: "MINIMUM_VARIANCE",
          included_asset_ids: ["asset-a", "asset-b"],
          parameters: {
            requested_asset_ids: ["asset-a", "asset-b"],
            bounds: body.bounds,
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
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    await createOptimizationRun({
      portfolio_id: "portfolio-1",
      method: "MINIMUM_VARIANCE",
      start: "2026-03-17",
      end: "2026-09-17",
      asset_ids: ["asset-a", "asset-b"],
      bounds: [
        { asset_id: "asset-a", minimum: 0, maximum: 0.7 },
        { asset_id: "asset-b", minimum: 0.3, maximum: 1 },
      ],
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/optimization-runs/",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });

  it("uses the list and owner-scoped detail endpoints", async () => {
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
