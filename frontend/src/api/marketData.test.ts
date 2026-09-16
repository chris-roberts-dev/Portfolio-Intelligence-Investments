import { fetchMarketBars } from "./marketData";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchMarketBars", () => {
  it("posts the canonical bounded market-bar request", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            results: [],
            meta: {
              provider: "mock",
              retrieved_at: "2026-09-16T13:00:00Z",
              interval: "1d",
              start: "2026-09-01",
              end: "2026-09-17",
            },
            row_count: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchMarketBars({
      symbols: ["AAPL", "MSFT"],
      start: "2026-09-01",
      end: "2026-09-17",
      interval: "1d",
      provider: "mock",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0]!;

    expect(String(url)).toBe("/api/v1/market-data/bars/query/");
    expect(init).toEqual(
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    expect(JSON.parse(String(init?.body))).toEqual({
      symbols: ["AAPL", "MSFT"],
      start: "2026-09-01",
      end: "2026-09-17",
      interval: "1d",
      provider: "mock",
    });
  });
});
