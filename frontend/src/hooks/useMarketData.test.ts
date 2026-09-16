import { marketBarQueryKey } from "./useMarketData";

describe("marketBarQueryKey", () => {
  it("includes symbol order, dates, interval, and provider", () => {
    expect(
      marketBarQueryKey({
        symbols: ["MSFT", "AAPL"],
        start: "2026-09-01",
        end: "2026-09-17",
        interval: "1d",
        provider: "mock",
      }),
    ).toEqual([
      "market-data",
      "bars",
      ["MSFT", "AAPL"],
      "2026-09-01",
      "2026-09-17",
      "1d",
      "mock",
    ]);
  });

  it("distinguishes the default provider from an explicit provider", () => {
    const base = {
      symbols: ["AAPL"],
      start: "2026-09-01",
      end: "2026-09-17",
      interval: "1d" as const,
    };

    expect(marketBarQueryKey(base)).not.toEqual(
      marketBarQueryKey({ ...base, provider: "mock" }),
    );
  });
});
