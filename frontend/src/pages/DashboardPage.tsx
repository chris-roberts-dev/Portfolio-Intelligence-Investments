import { useMemo, type ChangeEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { StatePanel } from "../components/ui/StatePanel";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";
import {
  isPortfolioReportView,
  PORTFOLIO_REPORT_VIEW_LABELS,
  PortfolioReportSubview,
  type PortfolioReportView,
} from "../features/dashboard/PortfolioReportSubview";
import {
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import {
  formatDate,
  formatDateTime,
} from "../features/dashboard/formatting";
import { useDashboardSnapshot, usePortfolios } from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";

const REPORT_RANGES: readonly DashboardRange[] = [
  "MTD",
  "QTD",
  "YTD",
  "1Y",
  "3Y",
  "5Y",
  "ALL",
];
const ALL_DASHBOARD_RANGES: readonly DashboardRange[] = [
  "1W",
  "1M",
  "3M",
  "6M",
  "MTD",
  "QTD",
  "YTD",
  "1Y",
  "3Y",
  "5Y",
  "ALL",
];
const REPORT_NAVIGATION: readonly PortfolioReportView[] = [
  "report",
  "holdings",
  "allocation",
  "performance",
  "risk",
  "transactions",
];

function isDashboardRange(value: string | null): value is DashboardRange {
  return value !== null && ALL_DASHBOARD_RANGES.includes(value as DashboardRange);
}

function inclusiveEndDate(endExclusive: string): string {
  const [year, month, day] = endExclusive.split("-").map(Number);
  if (!year || !month || !day) {
    return endExclusive;
  }

  const date = new Date(Date.UTC(year, month - 1, day, 12));
  date.setUTCDate(date.getUTCDate() - 1);
  return [
    date.getUTCFullYear(),
    String(date.getUTCMonth() + 1).padStart(2, "0"),
    String(date.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

export function DashboardPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const portfoliosQuery = usePortfolios();
  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );
  const rangeParam = searchParams.get("range");
  const range: DashboardRange = isDashboardRange(rangeParam) ? rangeParam : "YTD";
  const viewParam = searchParams.get("view");
  const view: PortfolioReportView = isPortfolioReportView(viewParam)
    ? viewParam
    : "report";

  const request = useMemo(() => {
    if (!portfolioId || !selectedPortfolio) {
      return null;
    }

    const dates = resolveDashboardDateRange(
      range,
      selectedPortfolio.created_at,
      selectedPortfolio.ledger_inception_at,
    );
    return {
      portfolioId,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioId, range, selectedPortfolio]);

  const snapshotRequest = view === "transactions" ? null : request;
  const snapshotQuery = useDashboardSnapshot(snapshotRequest);
  const snapshot = snapshotQuery.data;
  const inceptionAt =
    selectedPortfolio?.ledger_inception_at ?? selectedPortfolio?.created_at ?? null;
  const inceptionDate = inceptionAt?.split("T")[0] ?? null;
  const benchmarkLabel =
    snapshot?.performance?.provenance.benchmark_symbol ??
    (selectedPortfolio?.benchmark_asset_id ? "Configured benchmark" : "Not configured");
  const reportStart = snapshot?.snapshot.effective_start ?? request?.start ?? null;
  const reportEndExclusive =
    snapshot?.snapshot.effective_end_exclusive ?? request?.end ?? null;
  const reportEnd = reportEndExclusive ? inclusiveEndDate(reportEndExclusive) : null;
  const viewLabel = PORTFOLIO_REPORT_VIEW_LABELS[view];

  function viewHref(targetView: PortfolioReportView): string {
    if (!portfolioId) {
      return "/portfolios";
    }

    const next = new URLSearchParams(searchParams);
    next.set("range", range);
    next.set("view", targetView);
    return `/portfolios/${encodeURIComponent(portfolioId)}/dashboard?${next.toString()}`;
  }

  const header = (
    <div className="portfolio-report-header mx-auto w-full max-w-[1440px] px-4 py-4 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="portfolio-report-screen-only flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
            <Link
              to="/portfolios"
              className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Portfolios
            </Link>
            <span aria-hidden="true">/</span>
            <span>Portfolio report</span>
            {view !== "report" ? (
              <>
                <span aria-hidden="true">/</span>
                <span>{viewLabel}</span>
              </>
            ) : null}
          </div>

          {portfoliosQuery.data && portfoliosQuery.data.length > 0 ? (
            <label className="portfolio-report-screen-only mt-2 block max-w-xl">
              <span className="sr-only">Portfolio</span>
              <select
                value={portfolioId ?? ""}
                onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                  if (event.target.value) {
                    const next = new URLSearchParams(searchParams);
                    next.set("range", range);
                    next.set("view", view);
                    navigate(
                      `/portfolios/${encodeURIComponent(event.target.value)}/dashboard?${next.toString()}`,
                    );
                  }
                }}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-lg font-semibold text-slate-950 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                {portfoliosQuery.data.map((portfolio) => (
                  <option key={portfolio.id} value={portfolio.id}>
                    {portfolio.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <h1 className="portfolio-report-print-title mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
            {selectedPortfolio?.name ?? "Portfolio report"}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            {viewLabel}
            {reportStart && reportEnd
              ? ` · ${formatDate(reportStart)} – ${formatDate(reportEnd)}`
              : ""}
          </p>
          <p className="mt-1 flex flex-wrap gap-x-2 gap-y-1 text-xs text-slate-500">
            <span>Benchmark: {benchmarkLabel}</span>
            <span aria-hidden="true">·</span>
            <span>Currency: {selectedPortfolio?.base_currency ?? "USD"}</span>
            <span aria-hidden="true">·</span>
            <span>
              Inception: {inceptionDate ? formatDate(inceptionDate) : "Not available"}
            </span>
            {snapshot ? (
              <>
                <span aria-hidden="true">·</span>
                <span>Provider: {snapshot.snapshot.provider}</span>
              </>
            ) : view === "transactions" ? (
              <>
                <span aria-hidden="true">·</span>
                <span>Source: transaction ledger</span>
              </>
            ) : null}
          </p>
        </div>

        <div className="portfolio-report-screen-only flex w-full flex-wrap items-center justify-end gap-3 xl:w-auto">
          <div
            role="group"
            className="flex flex-wrap rounded-xl border border-slate-200 bg-white p-1"
            aria-label="Portfolio report date range"
          >
            {REPORT_RANGES.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={range === option}
                onClick={() => {
                  const next = new URLSearchParams(searchParams);
                  next.set("range", option);
                  next.set("view", view);
                  setSearchParams(next, { replace: true });
                }}
                className={`min-h-9 rounded-lg px-3 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                  range === option
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                {option === "ALL" ? "Since Inception" : option}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            Print / Export PDF
          </button>

          {portfolioId ? (
            <Link
              to={`/activity?portfolio=${encodeURIComponent(portfolioId)}`}
              className="inline-flex min-h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm outline-none hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Add transaction
            </Link>
          ) : null}

          {portfolioId ? (
            <Link
              to={`/portfolios/${encodeURIComponent(portfolioId)}/manage?range=${encodeURIComponent(range)}`}
              className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Manage
            </Link>
          ) : null}
        </div>
      </div>

      <nav
        className="portfolio-report-screen-only mt-4 flex gap-1 overflow-x-auto border-b border-slate-200"
        aria-label="Portfolio report sections"
      >
        {REPORT_NAVIGATION.map((targetView) => {
          const isActive = view === targetView;
          return (
            <Link
              key={targetView}
              to={viewHref(targetView)}
              aria-current={isActive ? "page" : undefined}
              className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                isActive
                  ? "border-blue-600 text-blue-800"
                  : "border-transparent text-slate-600 hover:border-blue-300 hover:text-blue-800"
              }`}
            >
              {PORTFOLIO_REPORT_VIEW_LABELS[targetView]}
            </Link>
          );
        })}
      </nav>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <div className="portfolio-report-page">
        {snapshot ? (
          <div className="portfolio-report-print-context mb-4 hidden text-xs text-slate-600">
            <p>
              Data as of {formatDateTime(snapshot.snapshot.current_data_as_of)} · Snapshot {snapshot.snapshot.snapshot_id}
            </p>
          </div>
        ) : view === "transactions" ? (
          <div className="portfolio-report-print-context mb-4 hidden text-xs text-slate-600">
            <p>Data source: authoritative transaction ledger.</p>
          </div>
        ) : null}

        {!portfoliosQuery.isPending && portfoliosQuery.data && !selectedPortfolio ? (
          <StatePanel
            title="Portfolio not found"
            message="This portfolio is not available in the authenticated account scope."
            tone="error"
            action={
              <Link
                to="/portfolios"
                className="inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
              >
                Choose a portfolio
              </Link>
            }
          />
        ) : view === "report" ? (
          <DashboardOverview
            snapshot={snapshot}
            isLoading={snapshotQuery.isPending || portfoliosQuery.isPending}
            isFetching={snapshotQuery.isFetching && snapshot !== undefined}
            error={
              snapshotQuery.error instanceof Error
                ? snapshotQuery.error
                : portfoliosQuery.error instanceof Error
                  ? portfoliosQuery.error
                  : null
            }
            onRetry={() => {
              void portfoliosQuery.refetch();
              void snapshotQuery.refetch();
            }}
          />
        ) : portfolioId ? (
          <PortfolioReportSubview
            view={view}
            portfolioId={portfolioId}
            snapshot={snapshot}
            isLoading={
              view === "transactions"
                ? portfoliosQuery.isPending
                : snapshotQuery.isPending || portfoliosQuery.isPending
            }
            isFetching={snapshotQuery.isFetching && snapshot !== undefined}
            error={
              view === "transactions"
                ? portfoliosQuery.error instanceof Error
                  ? portfoliosQuery.error
                  : null
                : snapshotQuery.error instanceof Error
                  ? snapshotQuery.error
                  : portfoliosQuery.error instanceof Error
                    ? portfoliosQuery.error
                    : null
            }
            onRetry={() => {
              void portfoliosQuery.refetch();
              if (view !== "transactions") {
                void snapshotQuery.refetch();
              }
            }}
          />
        ) : null}

        {snapshot ? (
          <footer className="portfolio-report-footer mt-5 border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p>
                Snapshot {snapshot.snapshot.snapshot_id} · Engine {snapshot.snapshot.engine_version}
              </p>
              <p>Calculated {formatDateTime(snapshot.snapshot.calculated_at)}</p>
            </div>
            <p className="mt-2">
              Returns are time-weighted where performance is available. Contributions and withdrawals are external cash flows and are not presented as investment gains or losses. Report currency {snapshot.snapshot.base_currency}.
            </p>
          </footer>
        ) : view === "transactions" ? (
          <footer className="portfolio-report-footer mt-5 border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500">
            <p>
              Transactions are displayed from the complete persisted ledger and are not filtered by the selected report period. Transaction editing, deletion, and reconciliation are not exposed by the current contracts.
            </p>
          </footer>
        ) : null}
      </div>
    </DashboardShell>
  );
}
