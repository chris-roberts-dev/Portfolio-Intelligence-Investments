import {
  useMemo,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";

import { ApiError } from "../../api/client";
import {
  DOMAIN_CARD_CLASS,
  DOMAIN_CONTROL_CLASS,
  DOMAIN_PRIMARY_ACTION_CLASS,
  DOMAIN_SECONDARY_ACTION_CLASS,
} from "../../components/ui/domainStyles";
import {
  apiFieldErrors,
  firstFieldError,
} from "../portfolioManagement/apiErrors";
import { TransactionHistoryPanel } from "./TransactionHistoryPanel";
import {
  useAssetCatalog,
  useConfirmPortfolioTransactionImport,
  useCreatePortfolioTransaction,
  usePreviewPortfolioTransactionImport,
  useResolveAssets,
} from "../../hooks/usePortfolioData";
import type {
  AssetCatalogItem,
  PortfolioTransactionCreateRequest,
  TransactionImportPreview,
  TransactionType,
} from "../../types/portfolioManagement";

const MAX_TRANSACTION_IMPORT_BYTES = 256 * 1024;
const USER_TRANSACTION_CSV_TEMPLATE = [
  "transaction_type,occurred_at,asset_symbol,quantity,price,fees,cash_amount",
  "DEPOSIT,2026-01-02T14:00:00Z,,,,0,10000.00",
  "BUY,2026-01-03T15:30:00Z,AAPL,10,200.00,1.00,",
].join("\n");
const USER_TRANSACTION_CSV_TEMPLATE_URL = `data:text/csv;charset=utf-8,${encodeURIComponent(
  USER_TRANSACTION_CSV_TEMPLATE,
)}`;

function localDateTimeInputValue(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function confirmErrorPreview(error: unknown): TransactionImportPreview | null {
  if (!(error instanceof ApiError)) {
    return null;
  }

  const payload = error.payload;
  if (payload === null || typeof payload !== "object") {
    return null;
  }

  const preview = (payload as { preview?: unknown }).preview;
  if (preview === null || typeof preview !== "object") {
    return null;
  }

  return preview as TransactionImportPreview;
}

function displayValue(value: string | null): string {
  return value ?? "—";
}

interface TransactionWorkflowsProps {
  portfolioId: string;
}

export function TransactionWorkflows({
  portfolioId,
}: TransactionWorkflowsProps) {
  const assetCatalogQuery = useAssetCatalog();
  const transactionMutation = useCreatePortfolioTransaction(portfolioId);
  const resolveAssetsMutation = useResolveAssets();
  const previewMutation = usePreviewPortfolioTransactionImport(portfolioId);
  const confirmMutation = useConfirmPortfolioTransactionImport(portfolioId);

  const [transactionType, setTransactionType] =
    useState<TransactionType>("DEPOSIT");
  const [occurredAt, setOccurredAt] = useState(localDateTimeInputValue);
  const [assetId, setAssetId] = useState("");
  const [assetSymbolInput, setAssetSymbolInput] = useState("");
  const [assetResolutionMessage, setAssetResolutionMessage] = useState<string | null>(
    null,
  );
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [fees, setFees] = useState("0");
  const [cashAmount, setCashAmount] = useState("");
  const [transactionSuccess, setTransactionSuccess] = useState<string | null>(
    null,
  );

  const [csvText, setCsvText] = useState("");
  const [csvFileName, setCsvFileName] = useState<string | null>(null);
  const [csvFileError, setCsvFileError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  const transactionErrors = apiFieldErrors(transactionMutation.error);
  const serverConfirmPreview = confirmErrorPreview(confirmMutation.error);
  const importPreview = serverConfirmPreview ?? previewMutation.data ?? null;

  const requiresAsset =
    transactionType === "BUY" ||
    transactionType === "SELL" ||
    transactionType === "DIVIDEND";
  const requiresQuantityPrice =
    transactionType === "BUY" || transactionType === "SELL";
  const requiresCashAmount =
    transactionType === "DEPOSIT" ||
    transactionType === "WITHDRAWAL" ||
    transactionType === "DIVIDEND";

  const assetOptions = useMemo(
    () => assetCatalogQuery.data ?? [],
    [assetCatalogQuery.data],
  );
  const selectedAsset = useMemo(
    () => assetOptions.find((asset) => asset.id === assetId) ?? null,
    [assetId, assetOptions],
  );

  async function resolveTickerSymbol(): Promise<AssetCatalogItem | null> {
    const symbol = assetSymbolInput.trim().toUpperCase();
    setAssetResolutionMessage(null);

    if (!symbol) {
      setAssetResolutionMessage("Enter a ticker symbol to resolve.");
      return null;
    }

    const existing = assetOptions.find((asset) => asset.symbol === symbol);
    if (existing) {
      setAssetId(existing.id);
      setAssetSymbolInput(existing.symbol);
      setAssetResolutionMessage(
        `${existing.symbol} is already available as a canonical asset.`,
      );
      return existing;
    }

    try {
      const result = await resolveAssetsMutation.mutateAsync({ symbols: [symbol] });
      const outcome = result.outcomes[0];
      if (outcome?.status === "RESOLVED" && outcome.asset) {
        setAssetId(outcome.asset.id);
        setAssetSymbolInput(outcome.asset.symbol);
        setAssetResolutionMessage(
          `${outcome.asset.symbol} resolved to ${outcome.asset.name}.`,
        );
        return outcome.asset;
      }

      setAssetId("");
      setAssetResolutionMessage(
        outcome?.warning ??
          `${symbol} could not be resolved to a supported canonical USD stock or ETF.`,
      );
      return null;
    } catch (error) {
      setAssetId("");
      setAssetResolutionMessage(
        error instanceof Error ? error.message : "Ticker resolution failed.",
      );
      return null;
    }
  }

  async function handleTransactionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTransactionSuccess(null);

    if (!occurredAt) {
      return;
    }

    const parsedDate = new Date(occurredAt);
    if (Number.isNaN(parsedDate.getTime())) {
      return;
    }

    const request: PortfolioTransactionCreateRequest = {
      transaction_type: transactionType,
      occurred_at: parsedDate.toISOString(),
    };

    if (requiresAsset) {
      let canonicalAssetId = assetId;
      if (!canonicalAssetId && assetSymbolInput.trim()) {
        canonicalAssetId = (await resolveTickerSymbol())?.id ?? "";
      }
      request.asset_id = canonicalAssetId || null;
    }

    if (requiresQuantityPrice) {
      request.quantity = quantity || null;
      request.price = price || null;
      request.fees = fees || "0";
    }

    if (requiresCashAmount) {
      request.cash_amount = cashAmount || null;
    }

    try {
      const created = await transactionMutation.mutateAsync(request);
      setTransactionSuccess(
        `${created.transaction_type} transaction recorded. Server ledger state remains authoritative for portfolio holdings, cash, and analytics.`,
      );
      setQuantity("");
      setPrice("");
      setFees("0");
      setCashAmount("");
    } catch {
      // Server validation remains authoritative and is rendered below.
    }
  }

  async function handleCsvFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setCsvFileError(null);
    setImportSuccess(null);
    previewMutation.reset();
    confirmMutation.reset();
    setCsvText("");
    setCsvFileName(null);

    if (file === null) {
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setCsvFileError("Select a .csv file.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_TRANSACTION_IMPORT_BYTES) {
      setCsvFileError(
        `CSV files must be ${MAX_TRANSACTION_IMPORT_BYTES} bytes or smaller.`,
      );
      event.target.value = "";
      return;
    }

    try {
      const text = await file.text();
      setCsvText(text);
      setCsvFileName(file.name);
    } catch {
      setCsvFileError("The selected CSV file could not be read.");
      event.target.value = "";
    }
  }

  async function handlePreviewImport() {
    setImportSuccess(null);
    confirmMutation.reset();

    try {
      await previewMutation.mutateAsync({ csv_text: csvText });
    } catch {
      // Preview mutation renders the server error.
    }
  }

  async function handleConfirmImport() {
    if (!importPreview?.can_import || !csvText || confirmMutation.isPending) {
      return;
    }

    try {
      const result = await confirmMutation.mutateAsync({ csv_text: csvText });
      setImportSuccess(
        `${result.imported_count} transaction${
          result.imported_count === 1 ? "" : "s"
        } imported atomically.`,
      );
      setCsvText("");
      setCsvFileName(null);
      previewMutation.reset();
    } catch {
      // Confirmation may return a newly revalidated preview; render it.
    }
  }

  return (
    <div className="space-y-5">
      <TransactionHistoryPanel portfolioId={portfolioId} />

      <section
        className={DOMAIN_CARD_CLASS}
        aria-labelledby="manual-transaction-heading"
      >
        <h2
          id="manual-transaction-heading"
          className="text-lg font-semibold text-slate-950"
        >
          Add transaction
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
          Record one canonical ledger event. The backend validates transaction
          shape, canonical asset identity, and long-only ledger state before
          persistence.
        </p>

        <form
          className="mt-5 grid gap-4 sm:grid-cols-2"
          onSubmit={(event) => void handleTransactionSubmit(event)}
        >
          <label className="text-sm font-medium text-slate-700">
            Transaction type
            <select
              value={transactionType}
              onChange={(event) => {
                setTransactionType(event.target.value as TransactionType);
                setAssetId("");
                setAssetSymbolInput("");
                setAssetResolutionMessage(null);
                resolveAssetsMutation.reset();
                setQuantity("");
                setPrice("");
                setFees("0");
                setCashAmount("");
                transactionMutation.reset();
                setTransactionSuccess(null);
              }}
              className={`mt-1 block w-full ${DOMAIN_CONTROL_CLASS}`}
            >
              <option value="DEPOSIT">Deposit</option>
              <option value="WITHDRAWAL">Withdrawal</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
              <option value="DIVIDEND">Dividend</option>
            </select>
          </label>

          <label className="text-sm font-medium text-slate-700">
            Occurred at
            <input
              type="datetime-local"
              value={occurredAt}
              required
              onChange={(event) => setOccurredAt(event.target.value)}
              className={`mt-1 block w-full ${DOMAIN_CONTROL_CLASS}`}
            />
            <span className="mt-1 block text-xs font-normal text-slate-500">
              Browser-local time is sent as a timezone-aware UTC instant.
            </span>
          </label>

          {requiresAsset ? (
            <div className="sm:col-span-2">
              <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4">
                <div className="flex flex-wrap items-end gap-3">
                  <label className="min-w-[14rem] flex-1 text-sm font-medium text-slate-700">
                    Ticker symbol
                    <input
                      type="text"
                      autoCapitalize="characters"
                      spellCheck={false}
                      value={assetSymbolInput}
                      onChange={(event) => {
                        setAssetSymbolInput(event.target.value.toUpperCase());
                        setAssetId("");
                        setAssetResolutionMessage(null);
                        resolveAssetsMutation.reset();
                      }}
                      placeholder="e.g. AAPL or VTI"
                      className={`mt-1 block w-full uppercase ${DOMAIN_CONTROL_CLASS}`}
                      aria-describedby="ticker-resolution-help"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={
                      !assetSymbolInput.trim() || resolveAssetsMutation.isPending
                    }
                    onClick={() => void resolveTickerSymbol()}
                    className={DOMAIN_SECONDARY_ACTION_CLASS}
                  >
                    {resolveAssetsMutation.isPending ? "Resolving…" : "Resolve ticker"}
                  </button>
                </div>
                <p
                  id="ticker-resolution-help"
                  className="mt-2 text-xs leading-5 text-slate-600"
                >
                  Enter the ticker you know. The server resolves or discovers the
                  supported security and uses its canonical UUID internally; you do
                  not need to look up an ID first.
                </p>
                {assetResolutionMessage ? (
                  <p
                    className={`mt-2 text-sm ${
                      assetId ? "text-emerald-700" : "text-rose-700"
                    }`}
                    role="status"
                  >
                    {assetResolutionMessage}
                  </p>
                ) : null}
              </div>

              <label className="mt-3 block text-sm font-medium text-slate-700">
                Resolved / existing asset
                <select
                  value={assetId}
                  required
                  disabled={
                    assetCatalogQuery.isPending ||
                    assetCatalogQuery.error instanceof Error
                  }
                  onChange={(event) => {
                    const nextId = event.target.value;
                    setAssetId(nextId);
                    const nextAsset = assetOptions.find((asset) => asset.id === nextId);
                    setAssetSymbolInput(nextAsset?.symbol ?? "");
                    setAssetResolutionMessage(null);
                  }}
                  aria-invalid={
                    firstFieldError(transactionErrors, "asset_id") !== null
                  }
                  className={`mt-1 block w-full ${DOMAIN_CONTROL_CLASS} disabled:opacity-50`}
                >
                  <option value="">Resolve a ticker or choose an existing asset</option>
                  {assetOptions.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.symbol} — {asset.name} ({asset.exchange})
                    </option>
                  ))}
                </select>
              </label>

              {selectedAsset ? (
                <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  <span className="font-semibold text-slate-800">
                    {selectedAsset.symbol} · {selectedAsset.name}
                  </span>
                  <span className="ml-2">
                    {selectedAsset.exchange} · {selectedAsset.currency}
                  </span>
                  <code className="mt-1 block break-all font-mono text-[11px] text-slate-500">
                    Canonical ID: {selectedAsset.id}
                  </code>
                </div>
              ) : null}

              {firstFieldError(transactionErrors, "asset_id") ? (
                <span className="mt-1 block text-sm font-normal text-rose-700">
                  {firstFieldError(transactionErrors, "asset_id")}
                </span>
              ) : assetCatalogQuery.error instanceof Error ? (
                <span className="mt-1 flex flex-wrap items-center gap-2 text-sm font-normal text-rose-700">
                  Canonical assets could not load.
                  <button
                    type="button"
                    onClick={() => void assetCatalogQuery.refetch()}
                    className="font-semibold underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    Retry assets
                  </button>
                </span>
              ) : null}
            </div>
          ) : null}

          {requiresQuantityPrice ? (
            <>
              <label className="text-sm font-medium text-slate-700">
                Quantity
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="any"
                  value={quantity}
                  required
                  onChange={(event) => setQuantity(event.target.value)}
                  className={`mt-1 block w-full tabular-nums ${DOMAIN_CONTROL_CLASS}`}
                />
                {firstFieldError(transactionErrors, "quantity") ? (
                  <span className="mt-1 block text-sm font-normal text-rose-700">
                    {firstFieldError(transactionErrors, "quantity")}
                  </span>
                ) : null}
              </label>

              <label className="text-sm font-medium text-slate-700">
                Execution price
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="any"
                  value={price}
                  required
                  onChange={(event) => setPrice(event.target.value)}
                  className={`mt-1 block w-full tabular-nums ${DOMAIN_CONTROL_CLASS}`}
                />
                {firstFieldError(transactionErrors, "price") ? (
                  <span className="mt-1 block text-sm font-normal text-rose-700">
                    {firstFieldError(transactionErrors, "price")}
                  </span>
                ) : null}
              </label>

              <label className="text-sm font-medium text-slate-700">
                Fees
                <input
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="any"
                  value={fees}
                  onChange={(event) => setFees(event.target.value)}
                  className={`mt-1 block w-full tabular-nums ${DOMAIN_CONTROL_CLASS}`}
                />
                {firstFieldError(transactionErrors, "fees") ? (
                  <span className="mt-1 block text-sm font-normal text-rose-700">
                    {firstFieldError(transactionErrors, "fees")}
                  </span>
                ) : null}
              </label>
            </>
          ) : null}

          {requiresCashAmount ? (
            <label className="text-sm font-medium text-slate-700">
              Cash amount
              <input
                type="number"
                inputMode="decimal"
                min="0"
                step="any"
                value={cashAmount}
                required
                onChange={(event) => setCashAmount(event.target.value)}
                className={`mt-1 block w-full tabular-nums ${DOMAIN_CONTROL_CLASS}`}
              />
              {firstFieldError(transactionErrors, "cash_amount") ? (
                <span className="mt-1 block text-sm font-normal text-rose-700">
                  {firstFieldError(transactionErrors, "cash_amount")}
                </span>
              ) : null}
            </label>
          ) : null}

          <div className="sm:col-span-2">
            {firstFieldError(transactionErrors, "non_field_errors") ? (
              <p className="mb-3 text-sm text-rose-700" role="alert">
                {firstFieldError(transactionErrors, "non_field_errors")}
              </p>
            ) : transactionMutation.error instanceof Error ? (
              <p className="mb-3 text-sm text-rose-700" role="alert">
                {transactionMutation.error.message}
              </p>
            ) : null}

            {transactionSuccess ? (
              <p className="mb-3 text-sm text-emerald-700" role="status">
                {transactionSuccess}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={transactionMutation.isPending}
              className={DOMAIN_PRIMARY_ACTION_CLASS}
            >
              {transactionMutation.isPending ? "Recording…" : "Record transaction"}
            </button>
          </div>
        </form>
      </section>

      <section
        className={DOMAIN_CARD_CLASS}
        aria-labelledby="csv-import-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2
              id="csv-import-heading"
              className="text-lg font-semibold text-slate-950"
            >
              Import transactions from CSV
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
              Use ticker symbols directly in the preferred CSV format. Preview
              resolves supported tickers to canonical assets, validates the ledger,
              and never persists transaction rows. Confirmation re-resolves and
              commits only when every row passes validation.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs font-medium">
            <a
              href={USER_TRANSACTION_CSV_TEMPLATE_URL}
              download="portfolio-transactions-template.csv"
              className="text-blue-700 underline decoration-blue-200 underline-offset-4 hover:text-blue-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Download ticker CSV template
            </a>
            <span className="text-slate-500">Format: docs/transaction-import.md</span>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-end gap-3">
          <label className="text-sm font-medium text-slate-700">
            CSV file
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => void handleCsvFile(event)}
              className="mt-1 block max-w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-800 hover:file:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </label>

          <button
            type="button"
            disabled={!csvText || previewMutation.isPending}
            onClick={() => void handlePreviewImport()}
            className={DOMAIN_SECONDARY_ACTION_CLASS}
          >
            {previewMutation.isPending ? "Resolving and validating…" : "Resolve tickers and preview"}
          </button>
        </div>

        {csvFileName ? (
          <p className="mt-2 text-xs text-slate-500">
            Selected: {csvFileName}
          </p>
        ) : null}

        {csvFileError ? (
          <p className="mt-2 text-sm text-rose-700" role="alert">
            {csvFileError}
          </p>
        ) : previewMutation.error instanceof Error ? (
          <p className="mt-2 text-sm text-rose-700" role="alert">
            {previewMutation.error.message}
          </p>
        ) : null}

        {importPreview ? (
          <div className="mt-5">
            <div
              className="flex flex-wrap items-center gap-2 text-sm"
              role="status"
              aria-live="polite"
            >
              <span className="font-semibold text-slate-950">
                {importPreview.row_count} rows
              </span>
              <span className="text-emerald-700">
                {importPreview.valid_count} valid
              </span>
              <span className="text-rose-700">
                {importPreview.invalid_count} invalid
              </span>
              <span className="text-slate-500">· Atomic import</span>
            </div>

            <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full min-w-[980px] border-collapse text-left text-xs">
                <caption className="sr-only">
                  Transaction CSV validation preview
                </caption>
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    {[
                      "Row",
                      "Status",
                      "Type",
                      "Occurred at",
                      "Asset",
                      "Quantity",
                      "Price",
                      "Fees",
                      "Cash",
                      "Issues",
                    ].map((label) => (
                      <th key={label} scope="col" className="px-3 py-2 font-semibold">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {importPreview.rows.map((row) => (
                    <tr key={row.row_number} className="border-t border-slate-100">
                      <td className="px-3 py-3 tabular-nums">{row.row_number}</td>
                      <td className="px-3 py-3 font-semibold">
                        {row.valid ? "Valid" : "Invalid"}
                      </td>
                      <td className="px-3 py-3">{displayValue(row.transaction_type)}</td>
                      <td className="px-3 py-3">{displayValue(row.occurred_at)}</td>
                      <td className="px-3 py-3">
                        <div>
                          <span className="font-semibold text-slate-900">
                            {row.asset_symbol ?? (row.asset_id ? "Canonical asset" : "—")}
                          </span>
                          {row.asset_id ? (
                            <code className="mt-0.5 block break-all font-mono text-[10px] text-slate-500">
                              {row.asset_id}
                            </code>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-3 py-3 tabular-nums">
                        {displayValue(row.quantity)}
                      </td>
                      <td className="px-3 py-3 tabular-nums">
                        {displayValue(row.price)}
                      </td>
                      <td className="px-3 py-3 tabular-nums">
                        {displayValue(row.fees)}
                      </td>
                      <td className="px-3 py-3 tabular-nums">
                        {displayValue(row.cash_amount)}
                      </td>
                      <td className="px-3 py-3">
                        {row.issues.length === 0 ? (
                          "—"
                        ) : (
                          <ul className="space-y-1 text-rose-700">
                            {row.issues.map((issue, index) => (
                              <li key={`${issue.code}-${issue.field}-${index}`}>
                                {issue.code}: {issue.message}
                              </li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={!importPreview.can_import || confirmMutation.isPending}
                onClick={() => void handleConfirmImport()}
                className={DOMAIN_PRIMARY_ACTION_CLASS}
              >
                {confirmMutation.isPending
                  ? "Importing…"
                  : "Confirm atomic import"}
              </button>

              {!importPreview.can_import ? (
                <span className="text-sm text-slate-600">
                  Resolve every invalid row before import can be confirmed.
                </span>
              ) : null}
            </div>
          </div>
        ) : null}

        {confirmMutation.error instanceof Error ? (
          <p className="mt-3 text-sm text-rose-700" role="alert">
            Import was not committed: {confirmMutation.error.message}
          </p>
        ) : null}

        {importSuccess ? (
          <p className="mt-3 text-sm text-emerald-700" role="status">
            {importSuccess} Portfolio dashboard and analysis queries were
            invalidated for authoritative server refresh.
          </p>
        ) : null}
      </section>
    </div>
  );
}
