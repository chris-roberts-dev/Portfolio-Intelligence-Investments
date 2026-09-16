import { lazy, Suspense } from "react";

import { ApiError } from "../../api/client";
import { LazySection } from "../../components/ui/LazySection";
import { Skeleton } from "../../components/ui/Skeleton";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardSnapshotModule,
  DashboardSnapshotResult,
} from "../../types/dashboard";
import { PerformanceHero } from "./PerformanceHero";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";

const AllocationPanel = lazy(async () => {
  const module = await import("./AllocationPanel");
  return { default: module.AllocationPanel };
});

const HoldingsPanel = lazy(async () => {
  const module = await import("./HoldingsPanel");
  return { default: module.HoldingsPanel };
});

const MoversPanel = lazy(async () => {
  const module = await import("./MoversPanel");
  return { default: module.MoversPanel };
});

const ReviewItemsPanel = lazy(async () => {
  const module = await import("./ReviewItemsPanel");
  return { default: module.ReviewItemsPanel };
});

interface DashboardOverviewProps {
  snapshot: DashboardSnapshotResult | undefined;
  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  onRetry: () => void;
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

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 lg:col-span-8">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="mt-4 h-10 w-56" />
        <Skeleton className="mt-7 h-72 w-full" />
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 lg:col-span-4">
        <Skeleton className="h-5 w-40" />

        <div className="mt-6 space-y-4">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      </section>
    </div>
  );
}

function AllocationSkeleton() {
  return (
    <section
      className="min-h-[24rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading allocation"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-28" />
          <Skeleton className="mt-3 h-6 w-36" />
        </div>

        <Skeleton className="h-8 w-24" />
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }, (_, index) => (
          <Skeleton key={index} className="h-24 w-full" />
        ))}
      </div>

      <Skeleton className="mt-6 h-40 w-full" />
    </section>
  );
}

function HoldingsSkeleton() {
  return (
    <section
      className="min-h-[28rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading holdings"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-28" />
          <Skeleton className="mt-3 h-6 w-32" />
        </div>

        <Skeleton className="h-8 w-36" />
      </div>

      <div className="mt-8 space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <Skeleton key={index} className="h-20 w-full" />
        ))}
      </div>
    </section>
  );
}

function MoversSkeleton() {
  return (
    <section
      className="min-h-[26rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading movers"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-32" />
          <Skeleton className="mt-3 h-6 w-28" />
        </div>

        <Skeleton className="h-8 w-24" />
      </div>

      <Skeleton className="mt-6 h-11 w-full" />

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-40 w-full" />
        ))}
      </div>
    </section>
  );
}

function ReviewItemsSkeleton() {
  return (
    <section
      className="min-h-[24rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading data-quality review items"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-28" />
          <Skeleton className="mt-3 h-6 w-44" />
        </div>

        <Skeleton className="h-8 w-28" />
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-9 w-24" />
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {Array.from({ length: 3 }, (_, index) => (
          <Skeleton key={index} className="h-32 w-full" />
        ))}
      </div>
    </section>
  );
}

export function DashboardOverview({
  snapshot,
  isLoading,
  isFetching,
  error,
  onRetry,
}: DashboardOverviewProps) {
  if (isLoading && snapshot === undefined) {
    return <DashboardSkeleton />;
  }

  if (error !== null && snapshot === undefined) {
    const apiError = error instanceof ApiError ? error : null;
    const title =
      apiError?.status === 403
        ? "Portfolio access denied"
        : apiError?.status === 404
          ? "Portfolio not found"
          : "Dashboard could not load";

    return (
      <StatePanel
        title={title}
        message={error.message}
        tone="error"
        action={
          <button
            type="button"
            onClick={onRetry}
            className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Retry
          </button>
        }
      />
    );
  }

  if (snapshot === undefined) {
    return (
      <StatePanel
        title="No dashboard snapshot"
        message="No portfolio dashboard data is available for this request."
      />
    );
  }

  const performanceError = moduleError(snapshot, "PERFORMANCE");
  const summaryError = moduleError(snapshot, "SUMMARY");
  const allocationError = moduleError(snapshot, "ALLOCATION");
  const holdingsError = moduleError(snapshot, "HOLDINGS");
  const moversError = moduleError(snapshot, "MOVERS");
  const reviewItemsError = moduleError(snapshot, "REVIEW_ITEMS");

  const hasUsableDashboard =
    snapshot.performance !== null ||
    snapshot.summary !== null ||
    snapshot.allocation !== null ||
    snapshot.holdings !== null ||
    snapshot.movers !== null ||
    snapshot.review_items !== null;

  if (!hasUsableDashboard) {
    return (
      <StatePanel
        title="Portfolio data is not available yet"
        message="The dashboard snapshot loaded, but the performance, summary, allocation, holdings, movers, and review-items modules are unavailable for the selected period."
      />
    );
  }

  return (
    <div className="relative">
      {error !== null ? (
        <div
          className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          Refresh failed. Showing the most recent successful dashboard snapshot.
        </div>
      ) : null}

      {isFetching ? (
        <div
          className="pointer-events-none absolute -top-10 right-0 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800"
          role="status"
          aria-live="polite"
        >
          Refreshing snapshot…
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-8">
          <PerformanceHero
            performance={snapshot.performance}
            currency={snapshot.snapshot.base_currency}
            moduleError={performanceError}
          />
        </div>

        <div className="lg:col-span-4">
          <PortfolioSummaryCard
            summary={snapshot.summary}
            currency={snapshot.snapshot.base_currency}
            moduleError={summaryError}
          />
        </div>
      </div>

      <div className="mt-5">
        <Suspense fallback={<AllocationSkeleton />}>
          <AllocationPanel
            allocation={snapshot.allocation}
            currency={snapshot.snapshot.base_currency}
            moduleError={allocationError}
          />
        </Suspense>
      </div>

      <div className="mt-5">
        <LazySection fallback={<HoldingsSkeleton />}>
          <Suspense fallback={<HoldingsSkeleton />}>
            <HoldingsPanel
              holdings={snapshot.holdings}
              currency={snapshot.snapshot.base_currency}
              portfolioId={snapshot.snapshot.portfolio_id}
              moduleError={holdingsError}
            />
          </Suspense>
        </LazySection>
      </div>

      <div className="mt-5">
        <LazySection fallback={<MoversSkeleton />}>
          <Suspense fallback={<MoversSkeleton />}>
            <MoversPanel
              movers={snapshot.movers}
              portfolioId={snapshot.snapshot.portfolio_id}
              moduleError={moversError}
            />
          </Suspense>
        </LazySection>
      </div>

      <div className="mt-5">
        <LazySection fallback={<ReviewItemsSkeleton />}>
          <Suspense fallback={<ReviewItemsSkeleton />}>
            <ReviewItemsPanel
              key={snapshot.snapshot.snapshot_id}
              reviewItems={snapshot.review_items}
              isSnapshotComplete={snapshot.is_complete}
              moduleError={reviewItemsError}
            />
          </Suspense>
        </LazySection>
      </div>
    </div>
  );
}