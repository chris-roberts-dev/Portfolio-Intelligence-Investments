import { useMemo } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router";

import { MarketCandlestickChart } from "../components/charts/MarketCandlestickChart";
import { MarketPriceChart } from "../components/charts/MarketPriceChart";
import { DataQualityBadge } from "../components/ui/DataQualityBadge";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  isDashboardRange,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
} from "../features/dashboard/formatting";
import { useMarketBarQuery } from "../hooks/useMarketData";
import { useDashboardSnapshot, usePortfolios } from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type { DashboardHolding, DashboardSnapshotResult } from "../types/dashboard";
import type { MarketBarQueryRequest, MarketBarSymbolResult } from "../types/marketData";

interface HoldingRouteState {
  holding?: {
    assetId: string;
    symbol: string;
    name: string;
    assetType: string;
    currency: string;
  };
}

function rangeLabel(range: DashboardRange): string {
  return range === "ALL" ? "Since Inception" : range;
}

function holdingModuleError(snapshot: DashboardSnapshotResult): string | null {
  const state = snapshot.modules.find((candidate) => candidate.module === "HOLDINGS");

  if (!state || state.status === "AVAILABLE") {
    return null;
  }

  return state.detail ?? state.error_code ?? "Holdings are unavailable.";
}

function metricCard(label: string, value: string, context?: string) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
      <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </dt>
      <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-950">
        {value}
      </dd>
      {context ? (
        <dd className="mt-1 text-xs leading-5 text-slate-500">{context}</dd>
      ) : null}
    </div>
  );
}

function HoldingResearchSkeleton() {
  return (
    <div aria-label="Loading holding research">
      <Skeleton className="h-40 w-full rounded-2xl" />
      <div className="mt-5 grid gap-5 xl:grid-cols-12">
        <Skeleton className="h-72 w-full rounded-2xl xl:col-span-4" />
        <Skeleton className="h-72 w-full rounded-2xl xl:col-span-8" />
      </div>
      <Skeleton className="mt-5 h-[32rem] w-full rounded-2xl" />
    </div>
  );
}

function expectedMarketResult(
  results: MarketBarSymbolResult[] | undefined,
  assetId: string | undefined,
): MarketBarSymbolResult | null {
  if (!results || !assetId) {
    return null;
  }

  return results.find((result) => result.asset_id === assetId) ?? null;
}

function symbolMarketResult(
  results: MarketBarSymbolResult[] | undefined,
  symbol: string | undefined,
): MarketBarSymbolResult | null {
  if (!results || !symbol) {
    return null;
  }

  return results.find((result) => result.symbol === symbol) ?? null;
}

export function HoldingDetailPage() {
  const { portfolioId, assetId } = useParams<{
    portfolioId: string;
    assetId: string;
  }>();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const state = location.state as HoldingRouteState | null;
  const portfoliosQuery = usePortfolios();
  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );
  const rangeParam = searchParams.get("range");
  const range: DashboardRange = isDashboardRange(rangeParam) ? rangeParam : "YTD";

  const dashboardRequest = useMemo(() => {
    if (!portfolioId || !selectedPortfolio) {
      return null;
    }

    const dates = resolveDashboardDateRange(
      range,
      selectedPortfolio.created_at,
      selectedPortfolio.ledger_inception_at,
    );

    return {
      portfolioId,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioId, range, selectedPortfolio]);

  const snapshotQuery = useDashboardSnapshot(dashboardRequest);
  const snapshot = snapshotQuery.data;
  const holding = useMemo<DashboardHolding | undefined>(
    () => snapshot?.holdings?.holdings.find((candidate) => candidate.asset_id === assetId),
    [assetId, snapshot?.holdings?.holdings],
  );

  const marketRequest = useMemo<MarketBarQueryRequest | null>(() => {
    if (!holding || !snapshot) {
      return null;
    }

    return {
      symbols: [holding.symbol],
      start: snapshot.snapshot.effective_start,
      end: snapshot.snapshot.effective_end_exclusive,
      interval: "1d",
    };
  }, [holding, snapshot]);

  const marketQuery = useMarketBarQuery(marketRequest);
  const marketBatch = marketQuery.data;
  const canonicalMarketResult = expectedMarketResult(marketBatch?.results, assetId);
  const requestedSymbolResult = symbolMarketResult(marketBatch?.results, holding?.symbol);
  const identityMismatch =
    requestedSymbolResult !== null &&
    requestedSymbolResult.asset_id !== null &&
    requestedSymbolResult.asset_id !== assetId;

  const preservedSearch = location.search || `?range=${encodeURIComponent(range)}&view=holdings`;
  const backPath = portfolioId
    ? `/portfolios/${encodeURIComponent(portfolioId)}/dashboard${preservedSearch}`
    : "/portfolios";
  const title = holding?.symbol ?? state?.holding?.symbol ?? "Holding research";
  const name = holding?.name ?? state?.holding?.name ?? "Security holding";

  const marketExplorerPath = useMemo(() => {
    if (!portfolioId || !assetId || !holding || !marketRequest) {
      return null;
    }

    const params = new URLSearchParams();
    params.set("symbol", holding.symbol);
    params.set("asset", assetId);
    params.set("start", marketRequest.start);
    params.set("end", marketRequest.end);
    params.set("portfolio", portfolioId);
    params.set("range", range);
    params.set("view", searchParams.get("view") ?? "holdings");

    return `/market-data?${params.toString()}`;
  }, [assetId, holding, marketRequest, portfolioId, range, searchParams]);

  const header = (
    <div className="mx-auto flex min-h-24 w-full max-w-[1440px] flex-wrap items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link
            to="/portfolios"
            className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            Portfolios
          </Link>
          <span aria-hidden="true">/</span>
          <Link
            to={backPath}
            className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            Portfolio report
          </Link>
          <span aria-hidden="true">/</span>
          <span>Security research</span>
        </div>

        <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="truncate text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
            {title}
          </h1>
          <p className="truncate text-sm text-slate-500">{name}</p>
        </div>

        <p className="mt-1 text-xs text-slate-500">
          Portfolio {selectedPortfolio?.name ?? portfolioId ?? "unknown"} · {rangeLabel(range)}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Link
          to={backPath}
          className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          Back to portfolio
        </Link>
        {marketExplorerPath ? (
          <Link
            to={marketExplorerPath}
            className="inline-flex min-h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm outline-none hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Open in Market Data Explorer
          </Link>
        ) : null}
      </div>
    </div>
  );

  const pageError =
    portfoliosQuery.error instanceof Error
      ? portfoliosQuery.error
      : snapshotQuery.error instanceof Error
        ? snapshotQuery.error
        : null;
  const pageIsLoading =
    portfoliosQuery.isPending ||
    (selectedPortfolio !== undefined && snapshotQuery.isPending);

  return (
    <DashboardShell header={header}>
      {pageIsLoading ? (
        <HoldingResearchSkeleton />
      ) : pageError ? (
        <StatePanel
          title="Holding research could not load"
          message={pageError.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => {
                void portfoliosQuery.refetch();
                void snapshotQuery.refetch();
              }}
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Retry
            </button>
          }
        />
      ) : !selectedPortfolio ? (
        <StatePanel
          title="Portfolio not found"
          message="This portfolio is not available in the authenticated account scope."
          tone="error"
          action={
            <Link
              to="/portfolios"
              className="inline-flex rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Choose a portfolio
            </Link>
          }
        />
      ) : snapshot && holdingModuleError(snapshot) ? (
        <StatePanel
          title="Holdings unavailable"
          message={holdingModuleError(snapshot) ?? "Holdings are unavailable."}
          tone="error"
          action={
            <Link
              to={backPath}
              className="inline-flex rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Return to portfolio report
            </Link>
          }
        />
      ) : !holding ? (
        <StatePanel
          title="Holding not found"
          message="The canonical asset is not a current holding in this portfolio snapshot. Return to Holdings to choose an available security."
          tone="error"
          action={
            <Link
              to={backPath}
              className="inline-flex rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Return to holdings
            </Link>
          }
        />
      ) : (
        <div className="space-y-5">
          <section
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            aria-labelledby="holding-research-identity-heading"
          >
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                  Canonical security identity
                </p>
                <h2
                  id="holding-research-identity-heading"
                  className="mt-1 text-xl font-semibold text-slate-950"
                >
                  {holding.symbol} · {holding.name}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  {holding.asset_type} · {holding.currency}
                </p>
              </div>
              <DataQualityBadge quality={holding.data_quality} />
            </div>

            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-5 text-slate-600">
              <span className="font-semibold text-slate-800">Canonical asset UUID:</span>{" "}
              <code className="break-all font-mono text-slate-700">{holding.asset_id}</code>
            </div>
          </section>

          <div className="grid gap-5 xl:grid-cols-12">
            <section
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 xl:col-span-5"
              aria-labelledby="holding-position-context-heading"
            >
              <h2
                id="holding-position-context-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Portfolio position context
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Server-returned holding metrics for the same {rangeLabel(range)} report context.
              </p>

              <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                {metricCard("Quantity", holding.quantity)}
                {metricCard(
                  "Current price",
                  formatCurrency(holding.current_price, holding.currency),
                  holding.current_price_date
                    ? `Price date ${formatDate(holding.current_price_date)}`
                    : undefined,
                )}
                {metricCard(
                  "Market value",
                  formatCurrency(holding.market_value, selectedPortfolio.base_currency),
                )}
                {metricCard("Portfolio weight", formatPercent(holding.weight, 2))}
                {metricCard(
                  "Selected-period return",
                  formatPercent(holding.selected_period_return, 2),
                )}
                {metricCard(
                  "Contribution to return",
                  formatPercent(holding.contribution_to_return, 2),
                )}
              </dl>
            </section>

            <section
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 xl:col-span-7"
              aria-labelledby="holding-market-context-heading"
            >
              <h2
                id="holding-market-context-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Market Data research context
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Daily provider-neutral market bars for the holding&apos;s canonical symbol over the dashboard&apos;s effective reporting period.
              </p>

              {marketQuery.isPending && marketBatch === undefined ? (
                <div className="mt-4" aria-label="Loading holding market data">
                  <Skeleton className="h-24 w-full rounded-xl" />
                </div>
              ) : marketQuery.error instanceof Error && marketBatch === undefined ? (
                <div className="mt-4">
                  <StatePanel
                    title="Market data could not load"
                    message={marketQuery.error.message}
                    tone="error"
                    action={
                      <button
                        type="button"
                        onClick={() => void marketQuery.refetch()}
                        className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                      >
                        Retry market data
                      </button>
                    }
                  />
                </div>
              ) : marketBatch ? (
                <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                  {metricCard("Provider", marketBatch.meta.provider)}
                  {metricCard("Interval", marketBatch.meta.interval)}
                  {metricCard(
                    "Coverage",
                    `${formatDate(marketBatch.meta.start)} – ${formatDate(marketBatch.meta.end)}`,
                    "End date is exclusive.",
                  )}
                  {metricCard(
                    "Retrieved",
                    formatDateTime(marketBatch.meta.retrieved_at),
                  )}
                </dl>
              ) : null}

              <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-xs leading-5 text-blue-950">
                Portfolio selected-period return uses the dashboard&apos;s documented adjusted-close methodology. The market research charts below display the existing raw OHLC/close contract and do not recompute portfolio performance.
              </div>
            </section>
          </div>

          {identityMismatch ? (
            <StatePanel
              title="Canonical asset identity mismatch"
              message={`Market Data resolved ${holding.symbol} to ${requestedSymbolResult?.asset_id ?? "an unknown asset"}, which does not match portfolio asset ${holding.asset_id}. Research charts are withheld rather than substituting a different security.`}
              tone="error"
            />
          ) : canonicalMarketResult?.status === "SUCCEEDED" ? (
            <>
              <section
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                aria-labelledby="holding-price-history-heading"
              >
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                      Market Data
                    </p>
                    <h2
                      id="holding-price-history-heading"
                      className="mt-1 text-lg font-semibold text-slate-950"
                    >
                      Daily raw close history
                    </h2>
                  </div>
                  <span className="text-xs text-slate-500">
                    {canonicalMarketResult.bars.length} observation
                    {canonicalMarketResult.bars.length === 1 ? "" : "s"}
                  </span>
                </div>
                <MarketPriceChart results={[canonicalMarketResult]} />
              </section>

              <section
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                aria-labelledby="holding-candlestick-heading"
              >
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                    Price and volume
                  </p>
                  <h2
                    id="holding-candlestick-heading"
                    className="mt-1 text-lg font-semibold text-slate-950"
                  >
                    Candlestick detail
                  </h2>
                </div>
                <MarketCandlestickChart result={canonicalMarketResult} />
              </section>
            </>
          ) : requestedSymbolResult ? (
            <StatePanel
              title="Market research unavailable for this period"
              message={
                requestedSymbolResult.warnings[0] ??
                `Market Data returned ${requestedSymbolResult.status.toLowerCase().replaceAll("_", " ")} for ${holding.symbol}.`
              }
            />
          ) : marketBatch ? (
            <StatePanel
              title="Canonical market result unavailable"
              message="The market-data response did not include the portfolio holding's canonical asset identity. No security substitution was made."
              tone="error"
            />
          ) : null}

          {holding.warnings.length > 0 ? (
            <section
              className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"
              aria-labelledby="holding-research-warnings-heading"
            >
              <h2 id="holding-research-warnings-heading" className="font-semibold">
                Holding data-quality notes
              </h2>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {holding.warnings.map((warning) => (
                  <li key={`${warning.code}-${warning.observation_date ?? "none"}`}>
                    {warning.message}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      )}
    </DashboardShell>
  );
}
