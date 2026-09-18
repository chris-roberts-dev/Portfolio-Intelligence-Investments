import { useMemo } from "react";
import { Link, useSearchParams } from "react-router";

import { PerformanceChart } from "../components/charts/PerformanceChart";
import { OverviewAllocationChart } from "../components/overview/OverviewAllocationChart";
import { OverviewKpiCard } from "../components/overview/OverviewKpiCard";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatDecimalPercent,
  formatPercent,
} from "../features/dashboard/formatting";
import {
  isOverviewRange,
  OVERVIEW_RANGES,
  resolveOverviewDateRange,
  type OverviewRange,
} from "../features/overview/overviewRange";
import { useDashboardSnapshot, usePortfolios } from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type {
  DashboardMover,
  DashboardSnapshotResult,
  PerformanceDataQuality,
} from "../types/dashboard";

function freshnessPresentation(
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

function signedCurrency(
  value: string | null,
  currency: string,
): string {
  if (value === null) {
    return "Not available";
  }

  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    signDisplay: "exceptZero",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric);
}

function valueTone(value: string | null): "neutral" | "positive" | "negative" {
  if (value === null) {
    return "neutral";
  }

  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return "neutral";
  }

  return numeric > 0 ? "positive" : "negative";
}

function percentTone(value: number | null): "neutral" | "positive" | "negative" {
  if (value === null || !Number.isFinite(value) || value === 0) {
    return "neutral";
  }

  return value > 0 ? "positive" : "negative";
}

function OverviewSkeleton() {
  return (
    <div aria-label="Loading overview">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-32 w-full rounded-2xl" />
        ))}
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-12">
        <Skeleton className="h-[28rem] w-full rounded-2xl xl:col-span-8" />
        <Skeleton className="h-[28rem] w-full rounded-2xl xl:col-span-4" />
      </div>
    </div>
  );
}

function MoverRow({ mover }: { mover: DashboardMover }) {
  return (
    <li className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-slate-900">
          {mover.symbol}
        </p>
        <p className="truncate text-xs text-slate-500">{mover.name}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold tabular-nums text-slate-900">
          {formatPercent(mover.contribution_to_return)}
        </p>
        <p className="text-xs tabular-nums text-slate-500">
          Return {formatPercent(mover.selected_period_return)}
        </p>
      </div>
    </li>
  );
}

function OverviewContent({
  snapshot,
  ytdSnapshot,
  inceptionSnapshot,
  portfolioName,
  portfolioInceptionAt,
  range,
}: {
  snapshot: DashboardSnapshotResult;
  ytdSnapshot: DashboardSnapshotResult | undefined;
  inceptionSnapshot: DashboardSnapshotResult | undefined;
  portfolioName: string;
  portfolioInceptionAt: string;
  range: OverviewRange;
}) {
  const currency = snapshot.snapshot.base_currency;
  const summary = snapshot.summary;
  const performance = snapshot.performance;
  const analytics = snapshot.analytics;
  const movers = snapshot.movers;
  const allocation = snapshot.allocation;
  const reviewItems = snapshot.review_items;
  const ytdReturn = ytdSnapshot?.performance?.summary.cumulative_return ?? null;
  const ytdBenchmark =
    ytdSnapshot?.performance?.summary.benchmark_cumulative_return ?? null;
  const inceptionReturn =
    inceptionSnapshot?.performance?.summary.cumulative_return ?? null;
  const investmentGainLoss = performance?.summary.investment_gain_loss ?? null;
  const cagr = analytics?.cagr ?? null;
  const contributors = movers?.largest_contributors.slice(0, 3) ?? [];
  const detractors = movers?.largest_detractors.slice(0, 1) ?? [];

  return (
    <>
      <section aria-labelledby="your-portfolio-heading">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="your-portfolio-heading" className="text-lg font-semibold text-slate-950">
              Your Portfolio
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {portfolioName} · authoritative server metrics
            </p>
          </div>
          <span className="text-xs text-slate-500">
            Selected range {range}
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <OverviewKpiCard
            label="Total Value"
            value={formatCurrency(summary?.metrics.total_market_value ?? null, currency)}
            context={
              snapshot.snapshot.current_data_as_of
                ? `As of ${formatDateTime(snapshot.snapshot.current_data_as_of)}`
                : "Current valuation date unavailable"
            }
          />
          <OverviewKpiCard
            label="YTD Return"
            value={formatPercent(ytdReturn, 1)}
            valueTone={percentTone(ytdReturn)}
            context={`Benchmark ${formatPercent(ytdBenchmark, 1)}`}
          />
          <OverviewKpiCard
            label="Since Inception"
            value={formatPercent(inceptionReturn, 1)}
            valueTone={percentTone(inceptionReturn)}
            context={`Since ${formatDate(portfolioInceptionAt.split("T")[0] ?? portfolioInceptionAt)}`}
          />
          <OverviewKpiCard
            label="Investment Gain/Loss"
            value={signedCurrency(investmentGainLoss, currency)}
            valueTone={valueTone(investmentGainLoss)}
            context="Selected-period investment result"
          />
          <OverviewKpiCard
            label="CAGR"
            value={formatPercent(cagr?.value ?? null, 1)}
            valueTone={percentTone(cagr?.value ?? null)}
            context={
              cagr
                ? `Compound annual growth rate · ${cagr.elapsed_days} elapsed days${
                    cagr.is_short_period ? " · annualized short period" : ""
                  }`
                : "Compound annual growth rate is not available for the selected period"
            }
          />
          <OverviewKpiCard
            label="Risk Level"
            value={formatPercent(analytics?.annualized_volatility ?? null, 1)}
            context="Annualized volatility; no synthetic risk label"
          />
        </div>
      </section>

      <div className="mt-5 grid gap-5 xl:grid-cols-12">
        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-8"
          aria-labelledby="overview-performance-heading"
        >
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 id="overview-performance-heading" className="text-lg font-semibold text-slate-950">
                Portfolio Performance
              </h2>
              <p className="text-sm text-slate-500">
                Cumulative time-weighted return · {range}
              </p>
            </div>
            <span className="text-xs text-slate-500">
              {performance?.provenance.benchmark_symbol ?? "Benchmark not configured"}
            </span>
          </div>

          {performance ? (
            <PerformanceChart
              performance={performance}
              currency={currency}
              mode="RETURN"
            />
          ) : (
            <StatePanel
              title="Performance unavailable"
              message="The server did not return portfolio performance for this period."
            />
          )}
        </section>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-4"
          aria-labelledby="overview-allocation-heading"
        >
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h2 id="overview-allocation-heading" className="text-lg font-semibold text-slate-950">
                Asset Allocation
              </h2>
              <p className="text-sm text-slate-500">
                Current server-valued allocation
              </p>
            </div>
            <Link
              to={`/allocation-lab?portfolio=${encodeURIComponent(snapshot.snapshot.portfolio_id)}&range=${encodeURIComponent(range)}`}
              className="text-xs font-semibold text-blue-700 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Open lab
            </Link>
          </div>

          {allocation?.allocation_available && allocation.groups.length > 0 ? (
            <OverviewAllocationChart groups={allocation.groups} />
          ) : (
            <StatePanel
              title="Allocation unavailable"
              message="Current allocation cannot be displayed from the available valuation data."
            />
          )}
        </section>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-12">
        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-7"
          aria-labelledby="overview-contributors-heading"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 id="overview-contributors-heading" className="text-lg font-semibold text-slate-950">
                Top Contributors
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Portfolio impact, not security return ranking
              </p>
            </div>
            <Link
              to={`/portfolios/${encodeURIComponent(snapshot.snapshot.portfolio_id)}/dashboard?range=1M`}
              className="text-xs font-semibold text-blue-700 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              View portfolio
            </Link>
          </div>

          {contributors.length > 0 || detractors.length > 0 ? (
            <div className="mt-3 grid gap-5 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Contributors
                </p>
                <ul className="mt-1">
                  {contributors.map((mover) => (
                    <MoverRow key={`contributor-${mover.asset_id}`} mover={mover} />
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                  Detractors
                </p>
                <ul className="mt-1">
                  {detractors.map((mover) => (
                    <MoverRow key={`detractor-${mover.asset_id}`} mover={mover} />
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Contribution attribution is not available for this period.
            </p>
          )}
        </section>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-5"
          aria-labelledby="overview-health-heading"
        >
          <h2 id="overview-health-heading" className="text-lg font-semibold text-slate-950">
            Portfolio Health
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Explainable risk and data-quality observations
          </p>

          <dl className="mt-4 divide-y divide-slate-100 text-sm">
            <div className="flex items-center justify-between gap-4 py-3 first:pt-0">
              <dt className="text-slate-600">Largest position</dt>
              <dd className="font-semibold tabular-nums text-slate-900">
                {formatPercent(analytics?.concentration?.largest_position_weight ?? null, 1)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-3">
              <dt className="text-slate-600">Cash level</dt>
              <dd className="font-semibold tabular-nums text-slate-900">
                {formatDecimalPercent(summary?.metrics.cash_percentage ?? null)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-3">
              <dt className="text-slate-600">Maximum drawdown</dt>
              <dd className="font-semibold tabular-nums text-slate-900">
                {formatPercent(analytics?.maximum_drawdown?.value ?? null, 1)}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4 py-3">
              <dt className="text-slate-600">Items needing review</dt>
              <dd className="font-semibold tabular-nums text-slate-900">
                {reviewItems?.counts.total ?? "Not available"}
              </dd>
            </div>
          </dl>

          {reviewItems?.items.length ? (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                Needs attention
              </p>
              <ul className="mt-2 space-y-2">
                {reviewItems.items.slice(0, 3).map((item) => (
                  <li key={item.key} className="flex gap-2 text-xs leading-5 text-slate-600">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" aria-hidden="true" />
                    <span>
                      <strong className="font-semibold text-slate-800">
                        {item.severity}:
                      </strong>{" "}
                      {item.message}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      </div>
    </>
  );
}

export function HomePage() {
  const portfoliosQuery = usePortfolios();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPortfolio = searchParams.get("portfolio");
  const rangeParam = searchParams.get("range");
  const range: OverviewRange = isOverviewRange(rangeParam) ? rangeParam : "YTD";
  const allPortfoliosSelected = requestedPortfolio === "all";

  const selectedPortfolio = useMemo(() => {
    if (allPortfoliosSelected) {
      return undefined;
    }

    const portfolios = portfoliosQuery.data ?? [];
    if (portfolios.length === 0) {
      return undefined;
    }

    return (
      portfolios.find((portfolio) => portfolio.id === requestedPortfolio) ??
      portfolios[0]
    );
  }, [allPortfoliosSelected, portfoliosQuery.data, requestedPortfolio]);

  const portfolioInceptionAt = selectedPortfolio
    ? selectedPortfolio.ledger_inception_at ?? selectedPortfolio.created_at
    : null;

  const selectedRequest = useMemo(() => {
    if (!selectedPortfolio) {
      return null;
    }

    const dates = resolveOverviewDateRange(
      range,
      portfolioInceptionAt ?? selectedPortfolio.created_at,
    );
    return {
      portfolioId: selectedPortfolio.id,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioInceptionAt, range, selectedPortfolio]);

  const ytdRequest = useMemo(() => {
    if (!selectedPortfolio) {
      return null;
    }

    const dates = resolveOverviewDateRange(
      "YTD",
      portfolioInceptionAt ?? selectedPortfolio.created_at,
    );
    return {
      portfolioId: selectedPortfolio.id,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioInceptionAt, selectedPortfolio]);

  const inceptionRequest = useMemo(() => {
    if (!selectedPortfolio) {
      return null;
    }

    const dates = resolveOverviewDateRange(
      "MAX",
      portfolioInceptionAt ?? selectedPortfolio.created_at,
    );
    return {
      portfolioId: selectedPortfolio.id,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioInceptionAt, selectedPortfolio]);

  const snapshotQuery = useDashboardSnapshot(selectedRequest);
  const ytdSnapshotQuery = useDashboardSnapshot(ytdRequest);
  const inceptionSnapshotQuery = useDashboardSnapshot(inceptionRequest);
  const snapshot = snapshotQuery.data;
  const freshness = freshnessPresentation(
    snapshot?.performance?.portfolio_data_quality,
    snapshot?.is_complete,
  );

  const topBarStart = (
    <div className="flex flex-wrap items-center gap-3">
      {portfoliosQuery.data && portfoliosQuery.data.length > 0 ? (
        <label className="flex items-center gap-2">
          <span className="sr-only">Overview portfolio</span>
          <select
            value={allPortfoliosSelected ? "all" : selectedPortfolio?.id ?? ""}
            onChange={(event) => {
              const next = new URLSearchParams(searchParams);
              next.set("portfolio", event.target.value);
              setSearchParams(next, { replace: true });
            }}
            className="max-w-56 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <option value="all">All Portfolios</option>
            {portfoliosQuery.data.map((portfolio) => (
              <option key={portfolio.id} value={portfolio.id}>
                {portfolio.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <span className="hidden text-xs text-slate-500 sm:inline">
        {snapshot?.snapshot.current_data_as_of
          ? `Market data as of ${formatDateTime(snapshot.snapshot.current_data_as_of)}`
          : "Market-data timestamp unavailable"}
      </span>

      {snapshot ? (
        <span
          className={`inline-flex rounded-full border px-2 py-1 text-[11px] font-semibold ${freshness.className}`}
        >
          {freshness.label}
        </span>
      ) : null}
    </div>
  );

  const header = (
    <div className="mx-auto flex min-h-24 w-full max-w-[1440px] flex-wrap items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
          Overview
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Here&apos;s how your portfolio is performing.
        </p>
      </div>

      <div className="flex w-full flex-wrap items-center justify-end gap-3 xl:w-auto">
        <div
          className="flex flex-wrap rounded-xl border border-slate-200 bg-white p-1"
          aria-label="Overview date range"
        >
          {OVERVIEW_RANGES.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={range === option}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("range", option);
                setSearchParams(next, { replace: true });
              }}
              className={`min-h-9 rounded-lg px-3 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                range === option
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              {option === "MAX" ? "Max" : option}
            </button>
          ))}
        </div>

        <Link
          to="/portfolios"
          className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          Manage portfolios
        </Link>

        <Link
          to={
            selectedPortfolio
              ? `/activity?portfolio=${encodeURIComponent(selectedPortfolio.id)}`
              : "/portfolios"
          }
          className="inline-flex min-h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm outline-none hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          Add transaction
        </Link>
      </div>
    </div>
  );

  return (
    <DashboardShell header={header} topBarStart={topBarStart}>
      {portfoliosQuery.isPending ? (
        <OverviewSkeleton />
      ) : portfoliosQuery.error instanceof Error ? (
        <StatePanel
          title="Portfolios could not load"
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
      ) : !portfoliosQuery.data?.length ? (
        <StatePanel
          title="Select or create a portfolio"
          message="Create your first portfolio in the Portfolios workspace, then add transactions to establish holdings and cash."
          action={
            <Link
              to="/portfolios"
              className="inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Create portfolio
            </Link>
          }
        />
      ) : allPortfoliosSelected ? (
        <StatePanel
          title="Consolidated overview is not available yet"
          message="All Portfolios is part of the new information architecture, but the backend does not yet expose an authoritative cross-portfolio performance contract. Select one portfolio to view server-authoritative analytics without client-side aggregation."
        />
      ) : !selectedPortfolio ? (
        <StatePanel
          title="Portfolio not found"
          message="The requested portfolio is not available in the authenticated account scope."
          tone="error"
        />
      ) : snapshotQuery.isPending || ytdSnapshotQuery.isPending || inceptionSnapshotQuery.isPending ? (
        <OverviewSkeleton />
      ) : snapshotQuery.error instanceof Error && !snapshot ? (
        <StatePanel
          title="Overview could not load"
          message={snapshotQuery.error.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => {
                void snapshotQuery.refetch();
                void ytdSnapshotQuery.refetch();
                void inceptionSnapshotQuery.refetch();
              }}
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Retry
            </button>
          }
        />
      ) : snapshot ? (
        <>
          {snapshotQuery.error instanceof Error ? (
            <div
              className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
              role="status"
            >
              Refresh failed. Showing the most recent successful overview snapshot.
            </div>
          ) : null}
          <OverviewContent
            snapshot={snapshot}
            ytdSnapshot={ytdSnapshotQuery.data}
            inceptionSnapshot={inceptionSnapshotQuery.data}
            portfolioName={selectedPortfolio.name}
            portfolioInceptionAt={portfolioInceptionAt ?? selectedPortfolio.created_at}
            range={range}
          />
        </>
      ) : (
        <StatePanel
          title="Overview data unavailable"
          message="No server snapshot is available for the selected portfolio and period."
        />
      )}
    </DashboardShell>
  );
}
