import {
  confirmPortfolioTransactionImport,
  createPortfolio,
  createPortfolioTransaction,
  deletePortfolio,
  fetchAssetCatalog,
  fetchDashboardSnapshot,
  fetchPortfolioAnalytics,
  fetchPortfolioTransactions,
  previewPortfolioTransactionImport,
  renamePortfolio,
  updatePortfolioBenchmark,
} from "./portfolios";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("portfolio read APIs", () => {
  it("requests the canonical owner-scoped snapshot with explicit range inputs", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            snapshot: {
              snapshot_id: "00000000-0000-0000-0000-000000000001",
            },
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardSnapshot({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-09-01",
      end: "2026-09-16",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/portfolios/00000000-0000-0000-0000-000000000002/dashboard/?start=2026-09-01&end=2026-09-16",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );
  });

  it("requests portfolio analytics with explicit range and user-selected rolling window only", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            portfolio_id: "00000000-0000-0000-0000-000000000002",
            observations: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchPortfolioAnalytics({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-03-16",
      end: "2026-09-17",
      rollingWindow: 21,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/portfolios/00000000-0000-0000-0000-000000000002/?start=2026-03-16&end=2026-09-17&rolling_window=21",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );

    const requestedUrl = String(fetchMock.mock.calls[0]?.[0]);

    expect(requestedUrl).not.toContain("risk_free_rate_annual");
    expect(requestedUrl).not.toContain(
      "minimum_acceptable_return_annual",
    );
  });

  it("does not send a hidden rolling-return window", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            portfolio_id: "00000000-0000-0000-0000-000000000002",
            observations: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchPortfolioAnalytics({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-03-16",
      end: "2026-09-17",
    });

    const requestedUrl = String(fetchMock.mock.calls[0]?.[0]);

    expect(requestedUrl).not.toContain("rolling_window");
    expect(requestedUrl).not.toContain("risk_free_rate_annual");
    expect(requestedUrl).not.toContain(
      "minimum_acceptable_return_annual",
    );
  });
});

describe("portfolio management APIs", () => {
  it("creates and renames portfolios with authenticated CSRF-safe mutations", async () => {
    document.cookie = "csrftoken=portfolio-management-test; path=/";
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            id: "00000000-0000-0000-0000-000000000002",
            name: "Portfolio",
            base_currency: "USD",
            benchmark_asset_id: null,
            created_at: "2026-09-16T12:00:00Z",
            updated_at: "2026-09-16T12:00:00Z",
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createPortfolio({ name: "Portfolio" });
    await renamePortfolio(
      "00000000-0000-0000-0000-000000000002",
      { name: "Renamed" },
    );

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/portfolios/");
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/v1/portfolios/00000000-0000-0000-0000-000000000002/",
    );
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ method: "PATCH", credentials: "include" }),
    );
  });


  it("deletes an owned empty portfolio with CSRF and accepts a 204 response", async () => {
    document.cookie = "csrftoken=portfolio-delete-test; path=/";
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(null, { status: 204 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await deletePortfolio("00000000-0000-0000-0000-000000000002");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/portfolios/00000000-0000-0000-0000-000000000002/",
      expect.objectContaining({
        method: "DELETE",
        credentials: "include",
        headers: expect.any(Headers),
      }),
    );

    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("X-CSRFToken")).toBe("portfolio-delete-test");
  });


  it("updates an owned portfolio benchmark with a canonical asset identity", async () => {
    document.cookie = "csrftoken=benchmark-management-test; path=/";
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            id: "00000000-0000-0000-0000-000000000002",
            name: "Portfolio",
            base_currency: "USD",
            benchmark_asset_id: "00000000-0000-0000-0000-000000000099",
            created_at: "2026-09-16T12:00:00Z",
            updated_at: "2026-09-16T12:00:00Z",
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await updatePortfolioBenchmark(
      "00000000-0000-0000-0000-000000000002",
      { benchmark_asset_id: "00000000-0000-0000-0000-000000000099" },
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/portfolios/00000000-0000-0000-0000-000000000002/benchmark/",
      expect.objectContaining({
        method: "PATCH",
        credentials: "include",
        body: JSON.stringify({
          benchmark_asset_id: "00000000-0000-0000-0000-000000000099",
        }),
      }),
    );
  });

  it("uses canonical asset and transaction ingestion endpoints", async () => {
    document.cookie = "csrftoken=transaction-management-test; path=/";
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, _init?: RequestInit) => {
        const url = String(input);
        const body = url.endsWith("/assets/") ? [] : {};
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const portfolioId = "00000000-0000-0000-0000-000000000002";
    await fetchAssetCatalog();
    await fetchPortfolioTransactions(portfolioId);
    await createPortfolioTransaction(portfolioId, {
      transaction_type: "DEPOSIT",
      occurred_at: "2026-09-16T12:00:00Z",
      cash_amount: "1000",
    });
    await previewPortfolioTransactionImport(portfolioId, {
      csv_text: "csv",
    });
    await confirmPortfolioTransactionImport(portfolioId, {
      csv_text: "csv",
    });

    expect(fetchMock.mock.calls.map((call) => String(call[0]))).toEqual([
      "/api/v1/assets/",
      `/api/v1/portfolios/${portfolioId}/transactions/`,
      `/api/v1/portfolios/${portfolioId}/transactions/`,
      `/api/v1/portfolios/${portfolioId}/transactions/import/preview/`,
      `/api/v1/portfolios/${portfolioId}/transactions/import/confirm/`,
    ]);
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
  });
});