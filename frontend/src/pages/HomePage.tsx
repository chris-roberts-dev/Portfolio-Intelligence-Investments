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

export function HomePage() {
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
      // Mutation state renders the server error without optimistic navigation.
    }
  }

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
          <p className="text-sm font-semibold text-blue-700">
            Portfolio analytics
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Select or create a portfolio
          </h2>
          <p className="mt-3 text-base leading-7 text-slate-600">
            Portfolios are owned by your authenticated account. Holdings and
            analytics remain derived from the authoritative transaction ledger.
          </p>
        </div>

        <section
          className="mb-8 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          aria-labelledby="create-portfolio-heading"
        >
          <h2
            id="create-portfolio-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Create portfolio
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            New portfolios use the current MVP base currency, USD. Add ledger
            transactions after creation to establish cash and holdings.
          </p>

          <form
            className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(event) => void handleCreatePortfolio(event)}
          >
            <label className="min-w-0 flex-1 text-sm font-medium text-slate-700">
              Portfolio name
              <input
                type="text"
                value={portfolioName}
                maxLength={255}
                required
                onChange={(event) => setPortfolioName(event.target.value)}
                aria-invalid={nameError !== null}
                aria-describedby={nameError ? "portfolio-name-error" : undefined}
                className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                placeholder="Long-term portfolio"
              />
            </label>

            <button
              type="submit"
              disabled={createPortfolioMutation.isPending || !portfolioName.trim()}
              className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createPortfolioMutation.isPending
                ? "Creating…"
                : "Create portfolio"}
            </button>
          </form>

          {nameError ? (
            <p
              id="portfolio-name-error"
              className="mt-2 text-sm text-rose-700"
              role="alert"
            >
              {nameError}
            </p>
          ) : createPortfolioMutation.error instanceof Error ? (
            <p className="mt-2 text-sm text-rose-700" role="alert">
              {createPortfolioMutation.error.message}
            </p>
          ) : null}
        </section>

        {portfoliosQuery.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, index) => (
              <Skeleton key={index} className="h-40 w-full" />
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
          <section aria-labelledby="owned-portfolios-heading">
            <h2
              id="owned-portfolios-heading"
              className="mb-3 text-lg font-semibold text-slate-950"
            >
              Your portfolios
            </h2>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {portfoliosQuery.data.map((portfolio) => (
                <article
                  key={portfolio.id}
                  className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                    {portfolio.base_currency} portfolio
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-slate-950">
                    {portfolio.name}
                  </h3>

                  <div className="mt-6 flex flex-wrap gap-3 text-sm font-semibold">
                    <Link
                      to={`/portfolios/${portfolio.id}/dashboard?range=1M`}
                      className="text-blue-700 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    >
                      Open dashboard →
                    </Link>
                    <Link
                      to={`/portfolios/${portfolio.id}/manage?range=1M`}
                      className="text-slate-700 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    >
                      Manage
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : (
          <StatePanel
            title="No portfolios yet"
            message="Create a portfolio above, then add a transaction manually or import the documented CSV format."
          />
        )}
      </div>
    </DashboardShell>
  );
}
