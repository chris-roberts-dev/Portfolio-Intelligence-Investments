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
  useAssetCatalog,
  useConfirmPortfolioTransactionImport,
  useCreatePortfolioTransaction,
  usePortfolioTransactions,
  usePreviewPortfolioTransactionImport,
} from "../../hooks/usePortfolioData";
import type {
  PortfolioTransactionCreateRequest,
  TransactionImportPreview,
  TransactionType,
} from "../../types/portfolioManagement";
import {
  apiFieldErrors,
  firstFieldError,
} from "../portfolioManagement/apiErrors";

const MAX_TRANSACTION_IMPORT_BYTES = 256 * 1024;

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

function formatLedgerDecimal(value: string | null): string {
  if (value === null) {
    return "—";
  }

  const [rawInteger, rawFraction = ""] = value.split(".");
  const sign = rawInteger.startsWith("-") ? "-" : "";
  const integerDigits = sign ? rawInteger.slice(1) : rawInteger;
  const groupedInteger = integerDigits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fraction = rawFraction.replace(/0+$/, "");

  return fraction
    ? `${sign}${groupedInteger}.${fraction}`
    : `${sign}${groupedInteger}`;
}

function formatOccurredAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

const TRANSACTION_TYPE_LABELS: Record<TransactionType, string> = {
  DEPOSIT: "Deposit",
  WITHDRAWAL: "Withdrawal",
  BUY: "Buy",
  SELL: "Sell",
  DIVIDEND: "Dividend",
};

function transactionTypeLabel(type: TransactionType): string {
  return TRANSACTION_TYPE_LABELS[type];
}

interface TransactionWorkflowsProps {
  portfolioId: string;
}

export function TransactionWorkflows({
  portfolioId,
}: TransactionWorkflowsProps) {
  const assetCatalogQuery = useAssetCatalog();
  const transactionsQuery = usePortfolioTransactions(portfolioId);
  const transactionMutation = useCreatePortfolioTransaction(portfolioId);
  const previewMutation = usePreviewPortfolioTransactionImport(portfolioId);
  const confirmMutation = useConfirmPortfolioTransactionImport(portfolioId);

  const [transactionType, setTransactionType] =
    useState<TransactionType>("DEPOSIT");
  const [occurredAt, setOccurredAt] = useState(localDateTimeInputValue);
  const [assetId, setAssetId] = useState("");
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
  const transactions = transactionsQuery.data ?? [];

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
      request.asset_id = assetId || null;
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
      <section
        className={DOMAIN_CARD_CLASS}
        aria-labelledby="transaction-history-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2
              id="transaction-history-heading"
              className="text-lg font-semibold text-slate-950"
            >
              Transaction history
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
              Every persisted ledger event for this portfolio, shown newest
              first. This is a read-only view of the server-authoritative
              transaction ledger.
            </p>
          </div>
          {transactionsQuery.data !== undefined ? (
            <span
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700"
              aria-label={`${transactions.length} transactions`}
            >
              {transactions.length} transaction{transactions.length === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>

        {transactionsQuery.isPending ? (
          <p className="mt-5 text-sm text-slate-500" role="status">
            Loading transaction history…
          </p>
        ) : transactionsQuery.error instanceof Error ? (
          <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-sm text-rose-800" role="alert">
              Transaction history could not load: {transactionsQuery.error.message}
            </p>
            <button
              type="button"
              onClick={() => void transactionsQuery.refetch()}
              className={`mt-3 ${DOMAIN_SECONDARY_ACTION_CLASS}`}
            >
              Retry transaction history
            </button>
          </div>
        ) : transactions.length === 0 ? (
          <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-600">
            No transactions have been recorded for this portfolio yet. Add one
            below or import a CSV to start the ledger.
          </div>
        ) : (
          <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[1120px] border-collapse text-left text-sm">
              <caption className="sr-only">
                Complete transaction history for the selected portfolio
              </caption>
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  {[
                    "Occurred at",
                    "Type",
                    "Asset",
                    "Quantity",
                    "Price (USD)",
                    "Fees (USD)",
                    "Cash amount (USD)",
                    "Ledger ID",
                  ].map((label) => (
                    <th key={label} scope="col" className="px-3 py-2.5 font-semibold">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction) => (
                  <tr
                    key={transaction.id}
                    className="border-t border-slate-100 align-top text-slate-700"
                  >
                    <td className="whitespace-nowrap px-3 py-3">
                      <time dateTime={transaction.occurred_at}>
                        {formatOccurredAt(transaction.occurred_at)}
                      </time>
                    </td>
                    <td className="px-3 py-3 font-semibold text-slate-950">
                      {transactionTypeLabel(transaction.transaction_type)}
                    </td>
                    <td className="px-3 py-3">
                      {transaction.asset_symbol ? (
                        <div>
                          <span className="font-semibold text-slate-950">
                            {transaction.asset_symbol}
                          </span>
                          {transaction.asset_id ? (
                            <code className="mt-0.5 block break-all font-mono text-[11px] text-slate-500">
                              {transaction.asset_id}
                            </code>
                          ) : null}
                        </div>
                      ) : (
                        "Cash"
                      )}
                    </td>
                    <td className="px-3 py-3 tabular-nums">
                      {formatLedgerDecimal(transaction.quantity)}
                    </td>
                    <td className="px-3 py-3 tabular-nums">
                      {formatLedgerDecimal(transaction.price)}
                    </td>
                    <td className="px-3 py-3 tabular-nums">
                      {formatLedgerDecimal(transaction.fees)}
                    </td>
                    <td className="px-3 py-3 tabular-nums">
                      {formatLedgerDecimal(transaction.cash_amount)}
                    </td>
                    <td className="px-3 py-3">
                      <code className="break-all font-mono text-[11px] text-slate-600">
                        {transaction.id}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

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
            <label className="text-sm font-medium text-slate-700 sm:col-span-2">
              Canonical asset
              <select
                value={assetId}
                required
                disabled={
                  assetCatalogQuery.isPending ||
                  assetCatalogQuery.error instanceof Error
                }
                onChange={(event) => setAssetId(event.target.value)}
                aria-invalid={
                  firstFieldError(transactionErrors, "asset_id") !== null
                }
                className={`mt-1 block w-full ${DOMAIN_CONTROL_CLASS} disabled:opacity-50`}
              >
                <option value="">Select an asset</option>
                {assetOptions.map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.symbol} — {asset.name} ({asset.exchange})
                  </option>
                ))}
              </select>
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
            </label>
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
              Preview never persists rows. Confirmation revalidates the file
              and commits only when every row passes canonical transaction and
              long-only ledger validation.
            </p>
          </div>
          <span className="text-xs font-medium text-slate-500">
            Format: docs/transaction-import.md
          </span>
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
            {previewMutation.isPending ? "Validating…" : "Validate and preview"}
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
                        {row.asset_symbol ?? displayValue(row.asset_id)}
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
