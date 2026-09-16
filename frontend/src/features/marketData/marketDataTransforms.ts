import type { PriceBar } from "../../types/marketData";

export interface CandlestickRow {
  date: string;
  value: [number, number, number, number];
  volume: number | null;
}

export function parseMarketSymbols(value: string): string[] {
  const symbols = value
    .split(/[\s,]+/u)
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(Boolean);

  return Array.from(new Set(symbols));
}

function finiteNumber(value: number | null): value is number {
  return value !== null && Number.isFinite(value);
}

export function buildCandlestickRows(
  bars: PriceBar[],
): CandlestickRow[] {
  return bars.flatMap((bar) => {
    if (
      !finiteNumber(bar.open) ||
      !finiteNumber(bar.close) ||
      !finiteNumber(bar.low) ||
      !finiteNumber(bar.high)
    ) {
      return [];
    }

    return [
      {
        date: bar.trade_date,
        value: [bar.open, bar.close, bar.low, bar.high],
        volume:
          bar.volume !== null && Number.isFinite(bar.volume)
            ? bar.volume
            : null,
      },
    ];
  });
}
