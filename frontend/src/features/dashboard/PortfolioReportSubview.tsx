import { lazy, Suspense } from "react";
import { Link } from "react-router";

import { ApiError } from "../../api/client";
import { Skeleton } from "../../components/ui/Skeleton";
import { StatePanel } from "../../components/ui/StatePanel";
import { TransactionHistoryPanel } from "../activity/TransactionHistoryPanel";
import type {
  DashboardSnapshotModule,
  DashboardSnapshotResult,
} from "../../types/dashboard";
import { PerformanceHero } from "./PerformanceHero";
import { PortfolioReportRisk } from "./PortfolioReportRisk";
import {
  formatCurrency,
  formatDate,
  formatPercent,
} from "./formatting";

const AllocationPanel = lazy(async () => {
  const module = await import("./AllocationPanel");
  return { default: module.AllocationPanel };
});

const HoldingsPanel = lazy(async () => {
  const module = await import("./HoldingsPanel");
  return { default: module.HoldingsPanel };
});

export type PortfolioReportView =
  | "report"
  | "holdings"
  | "allocation"
  | "performance"
  | "risk"
  | "transactions";

export const PORTFOLIO_REPORT_VIEWS: readonly PortfolioReportView[] = [
  "report",
  "holdings",
  "allocation",
  "performance",
  "risk",
  "transactions",
];

export const PORTFOLIO_REPORT_VIEW_LABELS: Record<PortfolioReportView, string> = {
  report: "Report",
  holdings: "Holdings",
  allocation: "Allocation",
  performance: "Performance",
  risk: "Risk",
  transactions: "Transactions",
};

export function isPortfolioReportView(
  value: string | null,
): value is PortfolioReportView {
  return (
    value !== null &&
    PORTFOLIO_REPORT_VIEWS.includes(value as PortfolioReportView)
  );
}

function moduleError(
  snapshot: DashboardSnapshotResult,
  module: DashboardSnapshotModule,
): string | null {
  const state = snapshot.modules.find((candidate) => candidate.module === module);

  if (!state || state.status === "AVAILABLE") {
    return null;
  }

  return state.detail ?? state.error_code ?? `${module} is unavailable.`;
}

function DetailHeading({
  view,
  description,
}: {
  view: Exclude<PortfolioReportView, "report">;
  description: string;
}) {
  return (
    <section
      className="portfolio-report-detail-header portfolio-report-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-labelledby="portfolio-report-detail-heading"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-700">
        Portfolio report detail
      </p>
      <h2
        id="portfolio-report-detail-heading"
        className="mt-1 text-2xl font-semibold tracking-tight text-slate-950"
      >
        {PORTFOLIO_REPORT_VIEW_LABELS[view]}
      </h2>
      <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
        {description}
      </p>
    </section>
  );
}

function DetailSkeleton({ label }: { label: string }) {
  return (
    <div aria-label={`Loading ${label.toLowerCase()} detail`}>
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="mt-3 h-8 w-52" />
        <Skeleton className="mt-3 h-5 w-full max-w-3xl" />
      </section>
      <Skeleton className="mt-4 h-[32rem] w-full rounded-2xl" />
    </div>
  );
}

function DetailError({
  error,
  onRetry,
}: {
  error: Error;
  onRetry: () => void;
}) {
  const apiError = error instanceof ApiError ? error : null;
  const title =
    apiError?.status === 403
      ? "Portfolio access denied"
      : apiError?.status === 404
        ? "Portfolio not found"
        : "Portfolio detail could not load";

  return (
    <StatePanel
      title={title}
      message={error.message}
      tone="error"
      action={
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          Retry
        </button>
      }
    />
  );
}

function PerformanceDetail({ snapshot }: { snapshot: DashboardSnapshotResult }) {
  const performance = snapshot.performance;
  const currency = snapshot.snapshot.base_currency;
  const performanceError = moduleError(snapshot, "PERFORMANCE");

  return (
    <div className="space-y-4">
      <PerformanceHero
        performance={performance}
        currency={currency}
        moduleError={performanceError}
      />

      {performance ? (
        <section
          className="portfolio-report-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          aria-labelledby="performance-period-details-heading"
        >
          <h3
            id="performance-period-details-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Performance period details
          </h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Values below are returned by the server performance contract for the
            same reporting period as the chart.
          </p>

          <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[
              ["Starting value", formatCurrency(performance.summary.starting_value, currency)],
              ["Ending value", formatCurrency(performance.summary.ending_value, currency)],
              ["Value change", formatCurrency(performance.summary.value_change, currency)],
              ["Net external flow", formatCurrency(performance.summary.net_external_flow, currency)],
              ["Investment gain/loss", formatCurrency(performance.summary.investment_gain_loss, currency)],
              ["Portfolio TWR", formatPercent(performance.summary.cumulative_return)],
              ["Benchmark return", formatPercent(performance.summary.benchmark_cumulative_return)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                  {label}
                </dt>
                <dd className="mt-1 text-base font-semibold tabular-nums text-slate-950">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
    </div>
  );
}

function ratio(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(value);
}

function RiskDetail({ snapshot }: { snapshot: DashboardSnapshotResult }) {
  const analytics = snapshot.analytics;
  const analyticsError = moduleError(snapshot, "ANALYTICS");

  return (
    <div className="space-y-4">
      <PortfolioReportRisk analytics={analytics} />

      <section
        className="portfolio-report-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        aria-labelledby="risk-calculation-context-heading"
      >
        <h3
          id="risk-calculation-context-heading"
          className="text-lg font-semibold text-slate-950"
        >
          Calculation context
        </h3>
        {analytics ? (
          <>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                  CAGR
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatPercent(analytics.cagr?.value ?? null)}
                </dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                  Benchmark correlation
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {ratio(analytics.benchmark_correlation?.value ?? null)}
                </dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                  HHI concentration index
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {ratio(analytics.concentration?.herfindahl_hirschman_index ?? null)}
                </dd>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                  Rolling-return window
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {analytics.rolling_return_window === null
                    ? "Not available"
                    : `${analytics.rolling_return_window} observations`}
                </dd>
              </div>
            </dl>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 p-4 text-sm leading-6 text-slate-600">
                <p className="font-semibold text-slate-950">Analytical provenance</p>
                <p className="mt-2">
                  Period {formatDate(analytics.provenance.period_start)} – {formatDate(analytics.provenance.period_end)}
                </p>
                <p>Data source {analytics.provenance.data_source}</p>
                <p>Price field {analytics.provenance.price_field}</p>
                <p>Annualization factor {analytics.provenance.annualization_factor}</p>
                <p>Benchmark {analytics.provenance.benchmark ?? "Not configured"}</p>
              </div>

              <div className="rounded-xl border border-slate-200 p-4 text-sm leading-6 text-slate-600">
                <p className="font-semibold text-slate-950">Warnings and assumptions</p>
                {analytics.warnings.length === 0 &&
                analytics.provenance.assumptions.length === 0 ? (
                  <p className="mt-2">No analytical warnings or additional assumptions were returned.</p>
                ) : (
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {analytics.warnings.map((warning) => (
                      <li key={`${warning.code}-${warning.message}`}>
                        {warning.message}
                      </li>
                    ))}
                    {analytics.provenance.assumptions.map((assumption) => (
                      <li key={assumption}>{assumption}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="mt-4">
            <StatePanel
              title="Risk analytics unavailable"
              message={
                analyticsError ??
                "The server did not return analytical context for this reporting period."
              }
            />
          </div>
        )}
      </section>
    </div>
  );
}

interface PortfolioReportSubviewProps {
  view: Exclude<PortfolioReportView, "report">;
  portfolioId: string;
  snapshot: DashboardSnapshotResult | undefined;
  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  onRetry: () => void;
}

export function PortfolioReportSubview({
  view,
  portfolioId,
  snapshot,
  isLoading,
  isFetching,
  error,
  onRetry,
}: PortfolioReportSubviewProps) {
  if (view === "transactions") {
    return (
      <div className="portfolio-report-detail space-y-4">
        <DetailHeading
          view="transactions"
          description="Review the complete persisted transaction ledger for this portfolio. The reporting-period selection is preserved for navigation, but ledger history is intentionally not filtered by that period."
        />
        <TransactionHistoryPanel portfolioId={portfolioId} />
        <section className="portfolio-report-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-950">Transaction work</h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Transaction editing, deletion, and reconciliation are not supported by the current backend contracts. Use Activity & Transactions to add a manual transaction or perform a previewed atomic CSV import.
          </p>
          <Link
            to={`/activity?portfolio=${encodeURIComponent(portfolioId)}`}
            className="portfolio-report-screen-only mt-4 inline-flex min-h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white outline-none hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Open Activity & Transactions
          </Link>
        </section>
      </div>
    );
  }

  if (isLoading && snapshot === undefined) {
    return <DetailSkeleton label={PORTFOLIO_REPORT_VIEW_LABELS[view]} />;
  }

  if (error !== null && snapshot === undefined) {
    return <DetailError error={error} onRetry={onRetry} />;
  }

  if (snapshot === undefined) {
    return (
      <StatePanel
        title="Portfolio detail unavailable"
        message="No server dashboard snapshot is available for this reporting period."
      />
    );
  }

  return (
    <div className="portfolio-report-detail space-y-4">
      {error !== null ? (
        <div
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          Refresh failed. Showing the most recent successful snapshot.
        </div>
      ) : null}
      {isFetching ? (
        <p className="text-right text-xs font-semibold text-blue-700" role="status" aria-live="polite">
          Refreshing snapshot…
        </p>
      ) : null}

      {view === "holdings" ? (
        <>
          <DetailHeading
            view="holdings"
            description="Inspect the current server-derived holdings with market value, portfolio weight, selected-period return, contribution, data quality, and security drill-down context."
          />
          <Suspense fallback={<DetailSkeleton label="Holdings" />}>
            <HoldingsPanel
              holdings={snapshot.holdings}
              currency={snapshot.snapshot.base_currency}
              portfolioId={snapshot.snapshot.portfolio_id}
              moduleError={moduleError(snapshot, "HOLDINGS")}
            />
          </Suspense>
        </>
      ) : null}

      {view === "allocation" ? (
        <>
          <DetailHeading
            view="allocation"
            description="Review the current authoritative asset-class and cash allocation, including the backend grouping methodology, data quality, and unclassified/other handling."
          />
          <Suspense fallback={<DetailSkeleton label="Allocation" />}>
            <AllocationPanel
              allocation={snapshot.allocation}
              currency={snapshot.snapshot.base_currency}
              moduleError={moduleError(snapshot, "ALLOCATION")}
            />
          </Suspense>
        </>
      ) : null}

      {view === "performance" ? (
        <>
          <DetailHeading
            view="performance"
            description="Review the selected-period time-weighted performance and benchmark series using the same snapshot, observation dates, provider, and methodology as the report summary."
          />
          <PerformanceDetail snapshot={snapshot} />
        </>
      ) : null}

      {view === "risk" ? (
        <>
          <DetailHeading
            view="risk"
            description="Review the server-returned risk metrics and their calculation context. No client-side thresholds or synthetic risk labels are applied."
          />
          <RiskDetail snapshot={snapshot} />
        </>
      ) : null}
    </div>
  );
}
