import { useMemo, type ChangeEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";

import { StatePanel } from "../components/ui/StatePanel";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";
import {
  DASHBOARD_RANGES,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import { formatDateTime } from "../features/dashboard/formatting";
import { useDashboardSnapshot, usePortfolios } from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type { PerformanceDataQuality } from "../types/dashboard";

function isDashboardRange(value: string | null): value is DashboardRange {
  return value !== null && DASHBOARD_RANGES.includes(value as DashboardRange);
}

function snapshotQuality(
  quality: PerformanceDataQuality | undefined,
  isComplete: boolean | undefined,
): { label: string; className: string } {
  if (quality === "STALE") {
    return {
      label: "Stale data",
      className: "border-amber-200 bg-amber-50 text-amber-900",
    };
  }

  if (quality === "PARTIAL" || isComplete === false) {
    return {
      label: "Partial data",
      className: "border-orange-200 bg-orange-50 text-orange-900",
    };
  }

  if (quality === "UNAVAILABLE") {
    return {
      label: "Unavailable",
      className: "border-rose-200 bg-rose-50 text-rose-900",
    };
  }

  return {
    label: "Current",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
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
  const range: DashboardRange = isDashboardRange(rangeParam) ? rangeParam : "1M";
  const request = useMemo(() => {
    if (!portfolioId || !selectedPortfolio) {
      return null;
    }

    const dates = resolveDashboardDateRange(range, selectedPortfolio.created_at);
    return {
      portfolioId,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioId, range, selectedPortfolio]);
  const snapshotQuery = useDashboardSnapshot(request);
  const snapshot = snapshotQuery.data;
  const freshness = snapshotQuality(
    snapshot?.performance?.portfolio_data_quality,
    snapshot?.is_complete,
  );

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link to="/" className="hover:text-slate-900">
            Overview
          </Link>
          <span aria-hidden="true">/</span>
          <span>Portfolio dashboard</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
            {selectedPortfolio?.name ?? "Portfolio dashboard"}
          </h1>
          {snapshot ? (
            <span
              className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${freshness.className}`}
            >
              {freshness.label}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex w-full flex-wrap items-center justify-end gap-3 sm:w-auto">
        {portfoliosQuery.data && portfoliosQuery.data.length > 0 ? (
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <span className="sr-only">Portfolio</span>
            <select
              value={portfolioId ?? ""}
              onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                if (event.target.value) {
                  navigate(`/portfolios/${event.target.value}/dashboard?range=${range}`);
                }
              }}
              className="max-w-52 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              {portfoliosQuery.data.map((portfolio) => (
                <option key={portfolio.id} value={portfolio.id}>
                  {portfolio.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {snapshot ? (
          <div className="text-right text-xs leading-5 text-slate-500">
            <p>{snapshot.snapshot.base_currency} · {snapshot.snapshot.provider}</p>
            <p>As of {formatDateTime(snapshot.snapshot.current_data_as_of)}</p>
          </div>
        ) : null}
      </div>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <section
        className="mb-5 flex flex-wrap items-center justify-between gap-4"
        aria-label="Dashboard period controls"
      >
        <div>
          <p className="text-sm font-medium text-slate-500">Selected period</p>
          <p className="mt-0.5 text-sm text-slate-700">
            {snapshot
              ? `${snapshot.snapshot.effective_start} to ${snapshot.snapshot.effective_end_exclusive}`
              : "Waiting for portfolio snapshot"}
          </p>

          {portfolioId && selectedPortfolio ? (
            <div className="mt-2 flex flex-wrap gap-4 text-sm font-semibold">
              <Link
                to={`/portfolios/${encodeURIComponent(
                  portfolioId,
                )}/analysis?range=${encodeURIComponent(range)}`}
                className="text-blue-700 outline-none underline decoration-blue-200 underline-offset-4 hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                View portfolio analysis →
              </Link>

              <Link
                to={`/allocation-lab?portfolio=${encodeURIComponent(
                  portfolioId,
                )}&range=${encodeURIComponent(range)}`}
                className="text-violet-700 outline-none underline decoration-violet-200 underline-offset-4 hover:text-violet-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                Open Allocation Lab →
              </Link>

              <Link
                to={`/portfolios/${encodeURIComponent(
                  portfolioId,
                )}/manage?range=${encodeURIComponent(range)}`}
                className="text-slate-700 outline-none underline decoration-slate-200 underline-offset-4 hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                Manage portfolio & transactions
              </Link>
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
          {DASHBOARD_RANGES.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={range === option}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("range", option);
                setSearchParams(next);
              }}
              className={`rounded-xl px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                range === option
                  ? "bg-slate-950 text-white"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              {option === "ALL" ? "All" : option}
            </button>
          ))}
        </div>
      </section>

      {!portfoliosQuery.isPending && portfoliosQuery.data && !selectedPortfolio ? (
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
      ) : (
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
      )}

      {snapshot ? (
        <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-slate-500">
          <p>
            Snapshot {snapshot.snapshot.snapshot_id} · Engine {snapshot.snapshot.engine_version}
          </p>
          <p>Calculated {formatDateTime(snapshot.snapshot.calculated_at)}</p>
        </footer>
      ) : null}
    </DashboardShell>
  );
}