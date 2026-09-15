import { Link } from "react-router";

import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import { DashboardShell } from "../layouts/DashboardShell";
import { usePortfolios } from "../hooks/usePortfolioData";

export function HomePage() {
  const portfoliosQuery = usePortfolios();
  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] items-center px-4 py-3 sm:px-6 lg:px-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
          Portfolio Intelligence
        </p>
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          Overview
        </h1>
      </div>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 max-w-2xl">
          <p className="text-sm font-semibold text-blue-700">Portfolio analytics</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Select a portfolio
          </h2>
          <p className="mt-3 text-base leading-7 text-slate-600">
            Open a coherent dashboard snapshot with portfolio value, selected-period
            performance, accounting context, and data freshness from the backend.
          </p>
        </div>

        {portfoliosQuery.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, index) => (
              <Skeleton key={index} className="h-36 w-full" />
            ))}
          </div>
        ) : portfoliosQuery.error instanceof Error ? (
          <StatePanel
            title="Portfolios could not load"
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
        ) : portfoliosQuery.data?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {portfoliosQuery.data.map((portfolio) => (
              <Link
                key={portfolio.id}
                to={`/portfolios/${portfolio.id}/dashboard?range=1M`}
                className="group rounded-3xl border border-slate-200 bg-white p-5 shadow-sm outline-none transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  {portfolio.base_currency} portfolio
                </p>
                <h3 className="mt-2 text-lg font-semibold text-slate-950 group-hover:text-blue-700">
                  {portfolio.name}
                </h3>
                <p className="mt-6 text-sm font-semibold text-blue-700">
                  Open dashboard →
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <StatePanel
            title="No portfolios yet"
            message="No owned portfolios are available for this account. Portfolio creation and transaction entry remain separate Phase 4 workflows."
          />
        )}
      </div>
    </DashboardShell>
  );
}
