import { Link, useLocation, useParams, useSearchParams } from "react-router";

import { DashboardShell } from "../layouts/DashboardShell";

interface HoldingRouteState {
  holding?: {
    assetId: string;
    symbol: string;
    name: string;
    assetType: string;
    currency: string;
  };
}

export function HoldingDetailPage() {
  const { portfolioId, assetId } = useParams<{
    portfolioId: string;
    assetId: string;
  }>();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const state = location.state as HoldingRouteState | null;
  const holding = state?.holding;
  const range = searchParams.get("range") ?? "1M";
  const preservedSearch = location.search || `?range=${encodeURIComponent(range)}`;
  const backPath = portfolioId
    ? `/portfolios/${encodeURIComponent(portfolioId)}/dashboard${preservedSearch}`
    : "/";
  const title = holding?.symbol ?? "Holding detail";

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link to={backPath} className="hover:text-slate-900">
            Portfolio dashboard
          </Link>
          <span aria-hidden="true">/</span>
          <span>Holding detail</span>
        </div>
        <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          {title}
        </h1>
      </div>
      <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
        Range {range}
      </span>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <div className="mx-auto max-w-4xl">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
            Detail route shell
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
            {holding?.name ?? "Security holding"}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {holding
              ? `${holding.assetType} · ${holding.currency}`
              : `Asset ${assetId ?? "unknown"}`}
          </p>

          <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
            <p className="font-semibold text-slate-950">Context preserved</p>
            <p className="mt-1 leading-6">
              Returning to the dashboard preserves portfolio {portfolioId ?? "unknown"} and
              the selected {range} time-range context. Detailed security analytics are
              intentionally deferred to a later Phase 4 holding-detail batch.
            </p>
          </div>

          <Link
            to={backPath}
            className="mt-6 inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            ← Back to portfolio dashboard
          </Link>
        </section>
      </div>
    </DashboardShell>
  );
}
