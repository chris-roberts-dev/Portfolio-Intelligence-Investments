import { useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router";

import { DomainPageHeader } from "../components/ui/DomainPageHeader";
import {
  DOMAIN_CARD_CLASS,
  DOMAIN_CONTROL_CLASS,
  DOMAIN_SECONDARY_ACTION_CLASS,
} from "../components/ui/domainStyles";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import { TransactionWorkflows } from "../features/activity/TransactionWorkflows";
import { usePortfolios } from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";

export function ActivityPage() {
  const portfoliosQuery = usePortfolios();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPortfolioId = searchParams.get("portfolio");

  const selectedPortfolio = useMemo(() => {
    const portfolios = portfoliosQuery.data ?? [];
    if (portfolios.length === 0) {
      return null;
    }

    return (
      portfolios.find((portfolio) => portfolio.id === requestedPortfolioId) ??
      portfolios[0]
    );
  }, [portfoliosQuery.data, requestedPortfolioId]);

  useEffect(() => {
    if (
      selectedPortfolio &&
      requestedPortfolioId !== selectedPortfolio.id
    ) {
      const next = new URLSearchParams(searchParams);
      next.set("portfolio", selectedPortfolio.id);
      setSearchParams(next, { replace: true });
    }
  }, [
    requestedPortfolioId,
    searchParams,
    selectedPortfolio,
    setSearchParams,
  ]);

  const topBarStart = selectedPortfolio ? (
    <label className="flex items-center gap-2">
      <span className="text-xs font-semibold text-slate-500">
        Portfolio
      </span>
      <select
        aria-label="Activity portfolio"
        value={selectedPortfolio.id}
        onChange={(event) => {
          const next = new URLSearchParams(searchParams);
          next.set("portfolio", event.target.value);
          setSearchParams(next, { replace: true });
        }}
        className={`max-w-64 ${DOMAIN_CONTROL_CLASS}`}
      >
        {(portfoliosQuery.data ?? []).map((portfolio) => (
          <option key={portfolio.id} value={portfolio.id}>
            {portfolio.name}
          </option>
        ))}
      </select>
    </label>
  ) : undefined;

  const header = (
    <DomainPageHeader
      eyebrow="Ledger workspace"
      title="Activity & Transactions"
      description="Review, record, and import activity for one owned portfolio while preserving the server-authoritative transaction ledger and validation rules."
      actions={
        selectedPortfolio ? (
          <Link
            to={`/portfolios/${encodeURIComponent(selectedPortfolio.id)}/manage?range=1M`}
            className={DOMAIN_SECONDARY_ACTION_CLASS}
          >
            Manage portfolio
          </Link>
        ) : undefined
      }
    />
  );

  return (
    <DashboardShell header={header} topBarStart={topBarStart}>
      {portfoliosQuery.isPending ? (
        <div aria-label="Loading Activity and Transactions">
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="mt-5 h-96 w-full rounded-2xl" />
        </div>
      ) : portfoliosQuery.error instanceof Error ? (
        <StatePanel
          title="Activity could not load"
          message={portfoliosQuery.error.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => void portfoliosQuery.refetch()}
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Retry
            </button>
          }
        />
      ) : !portfoliosQuery.data?.length ? (
        <StatePanel
          title="Create a portfolio before recording activity"
          message="Activity is always scoped to an owned portfolio UUID. Create a portfolio first, then return here to record or import transactions."
          action={
            <Link
              to="/portfolios"
              className="inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Create portfolio
            </Link>
          }
        />
      ) : selectedPortfolio ? (
        <>
          <section
            className={`${DOMAIN_CARD_CLASS} mb-5`}
            aria-labelledby="activity-scope-heading"
          >
            <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
              <div>
                <h2
                  id="activity-scope-heading"
                  className="text-lg font-semibold text-slate-950"
                >
                  {selectedPortfolio.name}
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  Canonical portfolio ID:{" "}
                  <code className="break-all font-mono text-xs text-slate-700">
                    {selectedPortfolio.id}
                  </code>
                </p>
              </div>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
                Ledger-backed
              </span>
            </div>
          </section>

          <TransactionWorkflows
            key={selectedPortfolio.id}
            portfolioId={selectedPortfolio.id}
          />

          <section
            className={`${DOMAIN_CARD_CLASS} mt-5`}
            aria-labelledby="unsupported-activity-heading"
          >
            <h2
              id="unsupported-activity-heading"
              className="text-lg font-semibold text-slate-950"
            >
              Current transaction capabilities
            </h2>
            <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-600">
              The current backend contract supports read-only transaction history,
              append-only manual transaction creation, plus CSV preview and atomic
              confirmation. Transaction-history editing, deletion, and
              reconciliation are not exposed by the current API, so this page does
              not present controls that would imply those capabilities exist.
            </p>
          </section>
        </>
      ) : (
        <StatePanel
          title="Portfolio not found"
          message="The requested portfolio UUID is not available in the authenticated account scope."
          tone="error"
        />
      )}
    </DashboardShell>
  );
}
