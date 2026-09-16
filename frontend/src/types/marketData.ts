export type MarketBarInterval = "1d";

export type MarketBarStatus =
  | "SUCCEEDED"
  | "NOT_FOUND"
  | "NO_DATA"
  | "FAILED";

export interface PriceBar {
  asset_id: string;
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  adjusted_close: number | null;
  volume: number | null;
  source: string;
  retrieved_at: string;
}

export interface MarketBarSymbolResult {
  symbol: string;
  asset_id: string | null;
  status: MarketBarStatus;
  bars: PriceBar[];
  warnings: string[];
}

export interface MarketBarBatchMeta {
  provider: string;
  retrieved_at: string;
  interval: MarketBarInterval;
  start: string;
  end: string;
}

export interface MarketBarBatchResult {
  results: MarketBarSymbolResult[];
  meta: MarketBarBatchMeta;
  row_count: number;
}

export interface MarketBarQueryRequest {
  symbols: string[];
  start: string;
  end: string;
  interval: MarketBarInterval;
  provider?: string;
}
