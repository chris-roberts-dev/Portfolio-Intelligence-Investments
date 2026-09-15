import { ApiError } from "../../api/client";
import { Skeleton } from "../../components/ui/Skeleton";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardSnapshotModule,
  DashboardSnapshotResult,
} from "../../types/dashboard";
import { PerformanceHero } from "./PerformanceHero";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";

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
  const hasUsableOverview = snapshot.performance !== null || snapshot.summary !== null;

  if (!hasUsableOverview) {
    return (
      <StatePanel
        title="Portfolio data is not available yet"
        message="The dashboard snapshot loaded, but the performance and summary modules are both unavailable for the selected period."
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
    </div>
  );
}
