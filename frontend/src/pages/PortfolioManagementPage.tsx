import {
  useEffect,
  useMemo,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import { Link, useParams, useSearchParams } from "react-router";

import { ApiError } from "../api/client";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  DASHBOARD_RANGES,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import {
  apiFieldErrors,
  firstFieldError,
} from "../features/portfolioManagement/apiErrors";
import {
  useAssetCatalog,
  useConfirmPortfolioTransactionImport,
  useCreatePortfolioTransaction,
  usePortfolios,
  usePreviewPortfolioTransactionImport,
  useRenamePortfolio,
  useUpdatePortfolioBenchmark,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type {
  PortfolioTransactionCreateRequest,
  TransactionImportPreview,
  TransactionType,
} from "../types/portfolioManagement";

const MAX_TRANSACTION_IMPORT_BYTES = 256 * 1024;

function isDashboardRange(value: string | null): value is DashboardRange {
  return value !== null && DASHBOARD_RANGES.includes(value as DashboardRange);
}

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

export function PortfolioManagementPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [searchParams] = useSearchParams();
  const rangeParam = searchParams.get("range");
  const range: DashboardRange = isDashboardRange(rangeParam) ? rangeParam : "1M";

  const portfoliosQuery = usePortfolios();
  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );
  const assetCatalogQuery = useAssetCatalog();

  const stablePortfolioId = portfolioId ?? "";
  const renameMutation = useRenamePortfolio(stablePortfolioId);
  const benchmarkMutation = useUpdatePortfolioBenchmark(stablePortfolioId);
  const transactionMutation = useCreatePortfolioTransaction(stablePortfolioId);
  const previewMutation = usePreviewPortfolioTransactionImport(stablePortfolioId);
  const confirmMutation = useConfirmPortfolioTransactionImport(stablePortfolioId);

  const [renameName, setRenameName] = useState("");
  const [benchmarkAssetId, setBenchmarkAssetId] = useState("");
  const [benchmarkSuccess, setBenchmarkSuccess] = useState<string | null>(null);
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

  useEffect(() => {
    if (selectedPortfolio) {
      setRenameName(selectedPortfolio.name);
      setBenchmarkAssetId(selectedPortfolio.benchmark_asset_id ?? "");
    }
  }, [selectedPortfolio]);

  const transactionErrors = apiFieldErrors(transactionMutation.error);
  const renameErrors = apiFieldErrors(renameMutation.error);
  const benchmarkErrors = apiFieldErrors(benchmarkMutation.error);
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

  const dashboardPath = portfolioId
    ? `/portfolios/${encodeURIComponent(portfolioId)}/dashboard?range=${encodeURIComponent(
        range,
      )}`
    : "/";

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link
            to={dashboardPath}
            className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Portfolio dashboard
          </Link>
          <span aria-hidden="true">/</span>
          <span>Manage portfolio</span>
        </div>
        <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          {selectedPortfolio?.name ?? "Portfolio management"}
        </h1>
      </div>

      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
        Ledger-backed
      </span>
    </div>
  );

  async function handleRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = renameName.trim();
    if (!name) {
      return;
    }

    try {
      await renameMutation.mutateAsync({ name });
    } catch {
      // Mutation state renders the server response.
    }
  }

  async function handleBenchmarkSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBenchmarkSuccess(null);

    try {
      const updated = await benchmarkMutation.mutateAsync({
        benchmark_asset_id: benchmarkAssetId || null,
      });
      setBenchmarkAssetId(updated.benchmark_asset_id ?? "");
      setBenchmarkSuccess(
        updated.benchmark_asset_id === null
          ? "Benchmark cleared."
          : "Benchmark selection saved.",
      );
    } catch {
      // Mutation state renders the stable server response.
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
        `${created.transaction_type} transaction recorded. Server ledger state will be used by the next dashboard and analysis reads.`,
      );
      setQuantity("");
      setPrice("");
      setFees("0");
      setCashAmount("");
    } catch {
      // Server errors remain authoritative and render below.
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
    if (
      !importPreview?.can_import ||
      !csvText ||
      confirmMutation.isPending
    ) {
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
      // Confirmation error may contain a newly revalidated preview.
    }
  }

  const assetOptions = useMemo(
    () => assetCatalogQuery.data ?? [],
    [assetCatalogQuery.data],
  );

  if (portfoliosQuery.isPending) {
    return (
      <DashboardShell header={header}>
        <Skeleton className="h-52 w-full" />
        <Skeleton className="mt-5 h-96 w-full" />
      </DashboardShell>
    );
  }

  if (portfoliosQuery.error instanceof Error) {
    return (
      <DashboardShell header={header}>
        <StatePanel
          title="Portfolio management could not load"
          message={portfoliosQuery.error.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => void portfoliosQuery.refetch()}
              className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Retry
            </button>
          }
        />
      </DashboardShell>
    );
  }

  if (!selectedPortfolio || !portfolioId) {
    return (
      <DashboardShell header={header}>
        <StatePanel
          title="Portfolio not found"
          message="This portfolio is not available in the authenticated account scope."
          tone="error"
          action={
            <Link
              to="/"
              className="inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Choose a portfolio
            </Link>
          }
        />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell header={header}>
      <div className="grid gap-5 xl:grid-cols-12 xl:items-start">
        <section
          className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 xl:col-span-4"
          aria-labelledby="rename-portfolio-heading"
        >
          <h2
            id="rename-portfolio-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Portfolio details
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Rename this owned portfolio. Base currency remains USD in the MVP.
          </p>

          <form
            className="mt-4"
            onSubmit={(event) => void handleRename(event)}
          >
            <label className="text-sm font-medium text-slate-700">
              Portfolio name
              <input
                type="text"
                value={renameName}
                maxLength={255}
                required
                onChange={(event) => setRenameName(event.target.value)}
                aria-invalid={firstFieldError(renameErrors, "name") !== null}
                className="mt-1 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              />
            </label>

            {firstFieldError(renameErrors, "name") ? (
              <p className="mt-2 text-sm text-rose-700" role="alert">
                {firstFieldError(renameErrors, "name")}
              </p>
            ) : renameMutation.error instanceof Error ? (
              <p className="mt-2 text-sm text-rose-700" role="alert">
                {renameMutation.error.message}
              </p>
            ) : null}

            {renameMutation.isSuccess ? (
              <p className="mt-2 text-sm text-emerald-700" role="status">
                Portfolio name saved.
              </p>
            ) : null}

            <button
              type="submit"
              disabled={renameMutation.isPending || !renameName.trim()}
              className="mt-4 rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
            >
              {renameMutation.isPending ? "Saving…" : "Save name"}
            </button>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-semibold text-slate-950">Benchmark</h3>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Select an active canonical USD stock or ETF. Benchmark-relative
              analytics are recalculated by the backend on the next read.
            </p>

            <form
              className="mt-3"
              onSubmit={(event) => void handleBenchmarkSubmit(event)}
            >
              <label className="text-sm font-medium text-slate-700">
                Benchmark asset
                <select
                  value={benchmarkAssetId}
                  aria-invalid={
                    firstFieldError(benchmarkErrors, "benchmark_asset_id") !== null
                  }
                  aria-describedby={
                    firstFieldError(benchmarkErrors, "benchmark_asset_id")
                      ? "benchmark-asset-error"
                      : undefined
                  }
                  onChange={(event) => {
                    setBenchmarkAssetId(event.target.value);
                    setBenchmarkSuccess(null);
                  }}
                  disabled={assetCatalogQuery.isPending || benchmarkMutation.isPending}
                  className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
                >
                  <option value="">No benchmark</option>
                  {assetOptions.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.symbol} — {asset.name}
                    </option>
                  ))}
                </select>
              </label>

              {assetCatalogQuery.error instanceof Error ? (
                <p className="mt-2 text-sm text-rose-700" role="alert">
                  Benchmark assets could not load. {assetCatalogQuery.error.message}
                </p>
              ) : firstFieldError(benchmarkErrors, "benchmark_asset_id") ? (
                <p
                  id="benchmark-asset-error"
                  className="mt-2 text-sm text-rose-700"
                  role="alert"
                >
                  {firstFieldError(benchmarkErrors, "benchmark_asset_id")}
                </p>
              ) : benchmarkMutation.error instanceof Error ? (
                <p className="mt-2 text-sm text-rose-700" role="alert">
                  {benchmarkMutation.error.message}
                </p>
              ) : null}

              {benchmarkSuccess ? (
                <p className="mt-2 text-sm text-emerald-700" role="status">
                  {benchmarkSuccess}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={assetCatalogQuery.isPending || benchmarkMutation.isPending}
                className="mt-3 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
              >
                {benchmarkMutation.isPending ? "Saving benchmark…" : "Save benchmark"}
              </button>
            </form>
          </div>
        </section>

        <section
          className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 xl:col-span-8"
          aria-labelledby="manual-transaction-heading"
        >
          <h2
            id="manual-transaction-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Add transaction
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Enter one canonical ledger event. Holdings, cash, cost basis, and
            analytics are recalculated only by existing backend services on
            subsequent reads.
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
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                className="mt-1 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              />
              <span className="mt-1 block text-xs font-normal text-slate-500">
                Your browser-local time is sent as a timezone-aware UTC instant.
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
                  className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
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
                      className="font-semibold underline underline-offset-4"
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
                    className="mt-1 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                    className="mt-1 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                    className="mt-1 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                  className="mt-1 block w-full rounded-xl border border-slate-200 px-3 py-2 text-sm tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                className="rounded-xl bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
              >
                {transactionMutation.isPending
                  ? "Recording…"
                  : "Record transaction"}
              </button>
            </div>
          </form>
        </section>
      </div>

      <section
        className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
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
              Import is atomic: every row must pass canonical transaction
              validation and long-only ledger replay before anything is
              committed. Preview never persists rows.
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
              className="mt-1 block max-w-full text-sm text-slate-700 file:mr-3 file:rounded-xl file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-800 hover:file:bg-slate-200"
            />
          </label>

          <button
            type="button"
            disabled={!csvText || previewMutation.isPending}
            onClick={() => void handlePreviewImport()}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
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

            <div className="mt-3 overflow-x-auto rounded-2xl border border-slate-200">
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
                className="rounded-xl bg-blue-700 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
            {importSuccess} Dashboard and analysis queries were invalidated for
            authoritative server refresh.
          </p>
        ) : null}
      </section>
    </DashboardShell>
  );
}
