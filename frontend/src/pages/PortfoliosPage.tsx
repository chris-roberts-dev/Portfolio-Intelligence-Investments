import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  apiFieldErrors,
  firstFieldError,
} from "../features/portfolioManagement/apiErrors";
import {
  useCreatePortfolio,
  usePortfolios,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";

export function PortfoliosPage() {
  const navigate = useNavigate();
  const portfoliosQuery = usePortfolios();
  const createPortfolioMutation = useCreatePortfolio();
  const [portfolioName, setPortfolioName] = useState("");
  const createErrors = apiFieldErrors(createPortfolioMutation.error);
  const nameError = firstFieldError(createErrors, "name");

  async function handleCreatePortfolio(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = portfolioName.trim();

    if (!name) {
      return;
    }

    try {
      const portfolio = await createPortfolioMutation.mutateAsync({ name });
      setPortfolioName("");
      navigate(`/portfolios/${portfolio.id}/manage?range=1M`);
    } catch {
      // Mutation state renders the authoritative server error.
    }
  }

  const header = (
    <div className="mx-auto flex min-h-24 w-full max-w-[1440px] flex-wrap items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">
          Portfolios
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Create, select, and manage your owned portfolio workspaces.
        </p>
      </div>
      <Link
        to="/"
        className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        Back to Overview
      </Link>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <div className="grid gap-5 xl:grid-cols-12">
        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-4"
          aria-labelledby="create-portfolio-heading"
        >
          <h2 id="create-portfolio-heading" className="text-lg font-semibold text-slate-950">
            Create portfolio
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            New portfolios use the current MVP base currency, USD. Holdings remain derived from the authoritative transaction ledger.
          </p>

          <form className="mt-5 space-y-3" onSubmit={(event) => void handleCreatePortfolio(event)}>
            <label className="block text-sm font-medium text-slate-700">
              Portfolio name
              <input
                type="text"
                value={portfolioName}
                maxLength={255}
                required
                onChange={(event) => setPortfolioName(event.target.value)}
                aria-invalid={nameError !== null}
                aria-describedby={nameError ? "portfolio-name-error" : undefined}
                className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                placeholder="Long-term portfolio"
              />
            </label>

            <button
              type="submit"
              disabled={createPortfolioMutation.isPending || !portfolioName.trim()}
              className="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white outline-none transition hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createPortfolioMutation.isPending ? "Creating…" : "Create portfolio"}
            </button>
          </form>

          {nameError ? (
            <p id="portfolio-name-error" className="mt-2 text-sm text-rose-700" role="alert">
              {nameError}
            </p>
          ) : createPortfolioMutation.error instanceof Error ? (
            <p className="mt-2 text-sm text-rose-700" role="alert">
              {createPortfolioMutation.error.message}
            </p>
          ) : null}
        </section>

        <section className="xl:col-span-8" aria-labelledby="owned-portfolios-heading">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 id="owned-portfolios-heading" className="text-lg font-semibold text-slate-950">
                Your portfolios
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Portfolio management is separate from the Overview dashboard.
              </p>
            </div>
          </div>

          {portfoliosQuery.isPending ? (
            <div className="grid gap-4 md:grid-cols-2">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton key={index} className="h-44 w-full rounded-2xl" />
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
                  className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
                >
                  Retry
                </button>
              }
            />
          ) : portfoliosQuery.data?.length ? (
            <div className="grid gap-4 md:grid-cols-2">
              {portfoliosQuery.data.map((portfolio) => (
                <article
                  key={portfolio.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                        {portfolio.base_currency} portfolio
                      </p>
                      <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
                        {portfolio.name}
                      </h3>
                    </div>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-semibold text-slate-600">
                      {portfolio.benchmark_asset_id ? "Benchmark set" : "No benchmark"}
                    </span>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    <Link
                      to={`/?portfolio=${encodeURIComponent(portfolio.id)}&range=YTD`}
                      className="inline-flex min-h-9 items-center rounded-lg bg-blue-600 px-3 text-xs font-semibold text-white outline-none hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    >
                      Open Overview
                    </Link>
                    <Link
                      to={`/portfolios/${portfolio.id}/dashboard?range=1M`}
                      className="inline-flex min-h-9 items-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
                    >
                      Detailed dashboard
                    </Link>
                    <Link
                      to={`/portfolios/${portfolio.id}/manage?range=1M`}
                      className="inline-flex min-h-9 items-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
                    >
                      Manage
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <StatePanel
              title="No portfolios yet"
              message="Create your first portfolio here, then add transactions manually or import the supported CSV format."
            />
          )}
        </section>
      </div>
    </DashboardShell>
  );
}
