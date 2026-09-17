import { resolveAssets } from "./portfolios";

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "csrftoken=; Max-Age=0; path=/";
});

describe("asset resolution API", () => {
  it("posts user symbols to the canonical server-side discovery boundary", async () => {
    document.cookie = "csrftoken=csrf-token; path=/";
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        symbols: ["QQQ", "NVDA"],
      });

      return new Response(
        JSON.stringify({
          provider: "yfinance",
          outcomes: [
            {
              symbol: "QQQ",
              status: "RESOLVED",
              asset: {
                id: "asset-qqq",
                symbol: "QQQ",
                name: "Invesco QQQ Trust",
                asset_type: "ETF",
                exchange: "NASDAQ",
                currency: "USD",
              },
              warning: null,
            },
            {
              symbol: "NVDA",
              status: "RESOLVED",
              asset: {
                id: "asset-nvda",
                symbol: "NVDA",
                name: "NVIDIA Corporation",
                asset_type: "STOCK",
                exchange: "NASDAQ",
                currency: "USD",
              },
              warning: null,
            },
          ],
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      );
    });

    vi.stubGlobal("fetch", fetchMock);

    const result = await resolveAssets({
      symbols: ["QQQ", "NVDA"],
    });

    expect(result.provider).toBe("yfinance");
    expect(result.outcomes.map((outcome) => outcome.asset?.id)).toEqual([
      "asset-qqq",
      "asset-nvda",
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/assets/resolve/",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });
});
