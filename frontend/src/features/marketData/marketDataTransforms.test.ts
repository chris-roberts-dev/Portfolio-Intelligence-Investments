import type { PriceBar } from "../../types/marketData";
import {
  buildCandlestickRows,
  parseMarketSymbols,
} from "./marketDataTransforms";

function bar(
  tradeDate: string,
  values: Partial<PriceBar> = {},
): PriceBar {
  return {
    asset_id: "00000000-0000-0000-0000-000000000011",
    trade_date: tradeDate,
    open: 10,
    high: 13,
    low: 9,
    close: 12,
    adjusted_close: 12,
    volume: 1000,
    source: "mock",
    retrieved_at: "2026-09-16T13:00:00Z",
    ...values,
  };
}

describe("market-data presentation transforms", () => {
  it("normalizes ticker entry and de-duplicates while preserving first order", () => {
    expect(
      parseMarketSymbols(" msft, AAPL\nmsft   spy,aapl "),
    ).toEqual(["MSFT", "AAPL", "SPY"]);
  });

  it("uses canonical ECharts candlestick tuple ordering and aligned volume dates", () => {
    const rows = buildCandlestickRows([
      bar("2026-09-14", {
        open: 100,
        close: 105,
        low: 98,
        high: 108,
        volume: 1200,
      }),
      bar("2026-09-15", {
        open: 106,
        close: 103,
        low: 101,
        high: 109,
        volume: 1500,
      }),
    ]);

    expect(rows).toEqual([
      {
        date: "2026-09-14",
        value: [100, 105, 98, 108],
        volume: 1200,
      },
      {
        date: "2026-09-15",
        value: [106, 103, 101, 109],
        volume: 1500,
      },
    ]);

    expect(rows.map((row) => row.date)).toEqual([
      "2026-09-14",
      "2026-09-15",
    ]);
    expect(rows.map((row) => row.volume)).toEqual([1200, 1500]);
  });

  it("omits incomplete OHLC bars instead of inventing candlestick values", () => {
    const rows = buildCandlestickRows([
      bar("2026-09-14", { low: null }),
      bar("2026-09-15"),
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0]?.date).toBe("2026-09-15");
  });
});
