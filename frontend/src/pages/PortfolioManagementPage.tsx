import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { DomainPageHeader } from "../components/ui/DomainPageHeader";
import {
  DOMAIN_CARD_CLASS,
  DOMAIN_CONTROL_CLASS,
  DOMAIN_PRIMARY_ACTION_CLASS,
  DOMAIN_SECONDARY_ACTION_CLASS,
} from "../components/ui/domainStyles";
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
  useDeletePortfolio,
  usePortfolios,
  useRenamePortfolio,
  useUpdatePortfolioBenchmark,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";

function isDashboardRange(value: string | null): value is DashboardRange {
  return value !== null && DASHBOARD_RANGES.includes(value as DashboardRange);
}

export function PortfolioManagementPage() {
  const navigate = useNavigate();
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
  const deleteMutation = useDeletePortfolio(stablePortfolioId);

  const [renameName, setRenameName] = useState("");
  const [benchmarkAssetId, setBenchmarkAssetId] = useState("");
  const [benchmarkSuccess, setBenchmarkSuccess] = useState<string | null>(null);
  const [deleteConfirmationOpen, setDeleteConfirmationOpen] = useState(false);
  const deleteButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (selectedPortfolio) {
      setRenameName(selectedPortfolio.name);
      setBenchmarkAssetId(selectedPortfolio.benchmark_asset_id ?? "");
    }
  }, [selectedPortfolio]);

  const renameErrors = apiFieldErrors(renameMutation.error);
  const benchmarkErrors = apiFieldErrors(benchmarkMutation.error);
  const assetOptions = useMemo(
    () => assetCatalogQuery.data ?? [],
    [assetCatalogQuery.data],
  );

  const dashboardPath = portfolioId
    ? `/portfolios/${encodeURIComponent(portfolioId)}/dashboard?range=${encodeURIComponent(
        range,
      )}`
    : "/portfolios";

  const activityPath = portfolioId
    ? `/activity?portfolio=${encodeURIComponent(portfolioId)}`
    : "/activity";

  const header = (
    <DomainPageHeader
      eyebrow="Portfolio configuration"
      title={selectedPortfolio?.name ?? "Portfolio management"}
      description="Maintain portfolio identity and benchmark configuration. Transaction ingestion now lives in Activity & Transactions."
      actions={
        <>
          <Link
            to={dashboardPath}
            className={DOMAIN_SECONDARY_ACTION_CLASS}
          >
            Portfolio dashboard
          </Link>
          <Link
            to={activityPath}
            className={DOMAIN_PRIMARY_ACTION_CLASS}
          >
            Open Activity & Transactions
          </Link>
        </>
      }
    />
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
      // Mutation state renders the authoritative server error.
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
      // Mutation state renders the authoritative server error.
    }
  }

  function closeDeleteConfirmation() {
    setDeleteConfirmationOpen(false);
    deleteButtonRef.current?.focus();
  }

  async function handleDeletePortfolio() {
    try {
      await deleteMutation.mutateAsync();
      setDeleteConfirmationOpen(false);
      navigate("/portfolios", { replace: true });
    } catch {
      // Mutation state renders the authoritative server error.
    }
  }

  if (portfoliosQuery.isPending) {
    return (
      <DashboardShell header={header}>
        <Skeleton className="h-52 w-full rounded-2xl" />
        <Skeleton className="mt-5 h-72 w-full rounded-2xl" />
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
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
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
              to="/portfolios"
              className="inline-flex rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
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
          className={`${DOMAIN_CARD_CLASS} xl:col-span-7`}
          aria-labelledby="portfolio-details-heading"
        >
          <h2
            id="portfolio-details-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Portfolio details
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Rename this owned portfolio. Base currency remains USD in the
            current MVP contract.
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
                className={`mt-1 block w-full ${DOMAIN_CONTROL_CLASS}`}
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
              className={`mt-4 ${DOMAIN_PRIMARY_ACTION_CLASS}`}
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
                  className={`mt-1 block w-full ${DOMAIN_CONTROL_CLASS} disabled:opacity-50`}
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
                className={`mt-3 ${DOMAIN_SECONDARY_ACTION_CLASS}`}
              >
                {benchmarkMutation.isPending ? "Saving benchmark…" : "Save benchmark"}
              </button>
            </form>
          </div>
        </section>

        <section
          className={`${DOMAIN_CARD_CLASS} xl:col-span-5`}
          aria-labelledby="transaction-work-heading"
        >
          <h2
            id="transaction-work-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Transaction work
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Manual entry and atomic CSV import are now centralized in the
            Activity & Transactions domain so portfolio configuration and ledger
            ingestion have clear homes.
          </p>
          <Link
            to={activityPath}
            className={`mt-5 ${DOMAIN_PRIMARY_ACTION_CLASS}`}
          >
            Add or import transactions
          </Link>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            The current API does not expose transaction-history editing,
            deletion, or reconciliation. Portfolio management does not invent
            controls for those unsupported operations.
          </p>
        </section>

        <section
          className={`${DOMAIN_CARD_CLASS} border-rose-200 xl:col-span-12`}
          aria-labelledby="portfolio-danger-zone-heading"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <h2
                id="portfolio-danger-zone-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Danger zone
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                Permanently delete this portfolio only if the server confirms it
                has no transaction ledger or persisted analytical history.
                Portfolios with retained history are protected from deletion.
              </p>
            </div>
            <button
              ref={deleteButtonRef}
              type="button"
              onClick={() => {
                deleteMutation.reset();
                setDeleteConfirmationOpen(true);
              }}
              className="inline-flex min-h-10 items-center justify-center rounded-lg border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-700 outline-none transition hover:bg-rose-50 focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2"
            >
              Delete portfolio
            </button>
          </div>
        </section>
      </div>

      {deleteConfirmationOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-8"
          role="presentation"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target && !deleteMutation.isPending) {
              closeDeleteConfirmation();
            }
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-portfolio-dialog-title"
            aria-describedby="delete-portfolio-dialog-description"
            className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl"
            onKeyDown={(event) => {
              if (event.key === "Escape" && !deleteMutation.isPending) {
                event.preventDefault();
                closeDeleteConfirmation();
                return;
              }

              if (event.key !== "Tab") {
                return;
              }

              const focusable = Array.from(
                event.currentTarget.querySelectorAll<HTMLButtonElement>(
                  "button:not([disabled])",
                ),
              );
              const first = focusable[0];
              const last = focusable.at(-1);

              if (!first || !last) {
                return;
              }

              if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
              } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
              }
            }}
          >
            <h2
              id="delete-portfolio-dialog-title"
              className="text-xl font-semibold text-slate-950"
            >
              Permanently delete {selectedPortfolio.name}?
            </h2>
            <p
              id="delete-portfolio-dialog-description"
              className="mt-2 text-sm leading-6 text-slate-600"
            >
              This action cannot be undone. The server will refuse deletion if
              the portfolio has any retained transaction or analytical history.
            </p>

            {deleteMutation.error instanceof Error ? (
              <p className="mt-4 text-sm text-rose-700" role="alert">
                {deleteMutation.error.message}
              </p>
            ) : null}

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                autoFocus
                disabled={deleteMutation.isPending}
                onClick={closeDeleteConfirmation}
                className={DOMAIN_SECONDARY_ACTION_CLASS}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => void handleDeletePortfolio()}
                className="inline-flex min-h-10 items-center justify-center rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-rose-800 focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleteMutation.isPending
                  ? "Deleting portfolio…"
                  : "Permanently delete portfolio"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </DashboardShell>
  );
}
