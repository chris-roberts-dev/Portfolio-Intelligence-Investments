export type TransactionType =
  | "DEPOSIT"
  | "WITHDRAWAL"
  | "BUY"
  | "SELL"
  | "DIVIDEND";

export interface AssetCatalogItem {
  id: string;
  symbol: string;
  name: string;
  asset_type: string;
  exchange: string;
  currency: string;
}

export interface PortfolioCreateRequest {
  name: string;
}

export interface PortfolioRenameRequest {
  name: string;
}

export interface PortfolioBenchmarkRequest {
  benchmark_asset_id: string | null;
}

export interface PortfolioTransactionCreateRequest {
  transaction_type: TransactionType;
  occurred_at: string;
  asset_id?: string | null;
  quantity?: string | null;
  price?: string | null;
  fees?: string;
  cash_amount?: string | null;
}

export interface PortfolioTransaction {
  id: string;
  portfolio_id: string;
  transaction_type: TransactionType;
  asset_id: string | null;
  asset_symbol: string | null;
  occurred_at: string;
  source_sequence: number;
  quantity: string | null;
  price: string | null;
  fees: string;
  cash_amount: string | null;
  created_at: string;
}

export interface TransactionImportRequest {
  csv_text: string;
}

export interface TransactionImportIssue {
  code: string;
  field: string;
  message: string;
}

export interface TransactionImportRowPreview {
  row_number: number;
  valid: boolean;
  transaction_type: string | null;
  occurred_at: string | null;
  asset_id: string | null;
  asset_symbol: string | null;
  quantity: string | null;
  price: string | null;
  fees: string | null;
  cash_amount: string | null;
  issues: TransactionImportIssue[];
}

export interface TransactionImportPreview {
  row_count: number;
  valid_count: number;
  invalid_count: number;
  can_import: boolean;
  atomic: boolean;
  rows: TransactionImportRowPreview[];
}

export interface TransactionImportResult {
  imported_count: number;
  transactions: PortfolioTransaction[];
}
