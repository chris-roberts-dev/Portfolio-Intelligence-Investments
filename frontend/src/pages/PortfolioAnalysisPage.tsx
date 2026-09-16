import { useMemo, type ReactNode } from "react";
import {
  Link,
  useParams,
  useSearchParams,
} from "react-router";

import { ApiError } from "../api/client";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  DASHBOARD_RANGES,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import {
  formatDate,
  formatPercent,
  humanizeCode,
} from "../features/dashboard/formatting";
import {
  usePortfolioAnalytics,
  usePortfolios,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type {
  EngineWarning,
  PortfolioAnalyticsResult,
  PortfolioAnalyticsWarningCode,
} from "../types/analytics";

function isDashboardRange(
  value: string | null,
): value is DashboardRange {
  return (
    value !== null &&
    DASHBOARD_RANGES.includes(value as DashboardRange)
  );
}

function formatUnsignedPercent(
  value: number | null,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatRatio(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatIndex(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(value);
}

function formatCount(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCurrencyNumber(
  value: number | null,
  currency: string,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function warningMessagesFor(
  analytics: PortfolioAnalyticsResult,
  codes: readonly PortfolioAnalyticsWarningCode[],
): string[] {
  const codeSet = new Set<PortfolioAnalyticsWarningCode>(codes);

  return analytics.warnings
    .filter((warning) => codeSet.has(warning.code))
    .map((warning) => warning.message);
}

function engineWarningMessages(
  warnings: EngineWarning[] | undefined,
): string[] {
  return warnings?.map((warning) => warning.message) ?? [];
}

function uniqueMessages(
  ...groups: readonly string[][]
): string[] {
  return Array.from(new Set(groups.flat()));
}

interface AnalysisMetricCardProps {
  label: string;
  value: string;
  description: string;
  diagnostics?: string[];
  footer?: ReactNode;
}

function AnalysisMetricCard({
  label,
  value,
  description,
  diagnostics = [],
  footer,
}: AnalysisMetricCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight text-slate-950">
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-slate-500">
        {description}
      </p>

      {diagnostics.length > 0 ? (
        <ul className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-xs leading-5 text-amber-900">
          {diagnostics.map((diagnostic) => (
            <li key={diagnostic}>{diagnostic}</li>
          ))}
        </ul>
      ) : null}

      {footer ? (
        <div className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">
          {footer}
        </div>
      ) : null}
    </article>
  );
}

function AnalysisSkeleton() {
  return (
    <div aria-label="Loading portfolio analysis">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-3 h-8 w-64" />
        <Skeleton className="mt-4 h-5 w-full max-w-2xl" />
      </section>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton
            key={index}
            className="h-40 w-full rounded-2xl"
          />
        ))}
      </div>
    </div>
  );
}

function AnalysisWarnings({
  analytics,
}: {
  analytics: PortfolioAnalyticsResult;
}) {
  if (analytics.warnings.length === 0) {
    return null;
  }

  return (
    <section
      className="mt-5 rounded-3xl border border-amber-200 bg-amber-50 p-5 sm:p-6"
      aria-labelledby="analysis-warnings-heading"
    >
      <h2
        id="analysis-warnings-heading"
        className="text-lg font-semibold tracking-tight text-amber-950"
      >
        Analytical warnings
      </h2>

      <p className="mt-1 text-sm leading-6 text-amber-900">
        These diagnostics come from the server calculation and explain
        unavailable or limited results.
      </p>

      <ul className="mt-4 space-y-3">
        {analytics.warnings.map((warning, index) => (
          <li
            key={`${warning.code}-${warning.observations ?? "none"}-${index}`}
            className="rounded-2xl border border-amber-200 bg-white/70 px-4 py-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-amber-200 bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-950">
                {humanizeCode(warning.code)}
              </span>

              {warning.observations !== null ? (
                <span className="text-xs text-amber-800">
                  {warning.observations} observations
                </span>
              ) : null}
            </div>

            <p className="mt-2 text-sm leading-6 text-amber-950">
              {warning.message}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AnalysisContent({
  analytics,
  currency,
}: {
  analytics: PortfolioAnalyticsResult;
  currency: string;
}) {
  const performanceUnavailable = warningMessagesFor(analytics, [
    "PERFORMANCE_UNAVAILABLE",
  ]);

  const insufficientHistory = warningMessagesFor(analytics, [
    "INSUFFICIENT_HISTORY",
  ]);

  const cagrWarnings = warningMessagesFor(analytics, [
    "PERFORMANCE_UNAVAILABLE",
    "UNDEFINED_CAGR",
  ]);

  const sharpeWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "INSUFFICIENT_HISTORY",
      "UNDEFINED_SHARPE",
    ]),
    engineWarningMessages(analytics.sharpe?.warnings),
  );

  const sortinoWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "INSUFFICIENT_HISTORY",
      "UNDEFINED_SORTINO",
    ]),
    engineWarningMessages(analytics.sortino?.warnings),
  );

  const drawdownWarnings = uniqueMessages(
    performanceUnavailable,
    engineWarningMessages(analytics.maximum_drawdown?.warnings),
  );

  const betaWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "BENCHMARK_NOT_CONFIGURED",
      "BENCHMARK_NOT_FOUND",
      "BENCHMARK_NO_DATA",
      "BENCHMARK_PROVIDER_FAILED",
      "UNDEFINED_BETA",
    ]),
    engineWarningMessages(analytics.beta?.warnings),
  );

  const correlationWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "BENCHMARK_NOT_CONFIGURED",
      "BENCHMARK_NOT_FOUND",
      "BENCHMARK_NO_DATA",
      "BENCHMARK_PROVIDER_FAILED",
      "UNDEFINED_CORRELATION",
    ]),
    engineWarningMessages(analytics.benchmark_correlation?.warnings),
  );

  const rollingWarnings = warningMessagesFor(analytics, [
    "INSUFFICIENT_ROLLING_HISTORY",
  ]);

  const allocationWarnings = warningMessagesFor(analytics, [
    "CURRENT_VALUATION_INCOMPLETE",
    "CURRENT_ALLOCATION_UNAVAILABLE",
  ]);

  const limitedHistory = analytics.warnings.some(
    (warning) => warning.code === "INSUFFICIENT_HISTORY",
  );

  const partialValuation = analytics.warnings.some(
    (warning) => warning.code === "CURRENT_VALUATION_INCOMPLETE",
  );

  const sourceWarnings = analytics.warnings.some(
    (warning) => warning.code === "SOURCE_WARNING",
  );

  return (
    <>
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
              Deterministic analytics
            </p>

            <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
              Analytical results
            </h2>

            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              All financial values below are supplied by the backend analytics
              contract. The frontend formats values and exposes diagnostics
              without recalculating portfolio metrics.
            </p>
          </div>

          <div
            className="flex flex-wrap gap-2"
            aria-label="Analysis status"
          >
            {limitedHistory ? (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
                Limited history
              </span>
            ) : null}

            {partialValuation ? (
              <span className="rounded-full border border-orange-200 bg-orange-50 px-2.5 py-1 text-xs font-semibold text-orange-900">
                Partial current valuation
              </span>
            ) : null}

            {sourceWarnings ? (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
                Source warnings
              </span>
            ) : null}

            {!limitedHistory && !partialValuation && !sourceWarnings ? (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                Analysis available
              </span>
            ) : null}
          </div>
        </div>
      </section>

      <section
        className="mt-5"
        aria-labelledby="return-risk-heading"
      >
        <div className="mb-3">
          <h2
            id="return-risk-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Return and risk
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Historical results for the server-provided effective analytical
            period.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <AnalysisMetricCard
            label="Cumulative return"
            value={formatPercent(analytics.cumulative_return)}
            description="Time-weighted cumulative portfolio return."
            diagnostics={performanceUnavailable}
          />

          <AnalysisMetricCard
            label="CAGR"
            value={formatPercent(analytics.cagr?.value ?? null)}
            description="Annualized geometric return using the server's elapsed-period convention."
            diagnostics={cagrWarnings}
            footer={
              analytics.cagr ? (
                <>
                  {analytics.cagr.elapsed_days} elapsed days
                  {analytics.cagr.is_short_period
                    ? " · Annualized short period"
                    : ""}
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Annualized volatility"
            value={formatUnsignedPercent(analytics.annualized_volatility)}
            description="Annualized sample volatility of daily portfolio returns."
            diagnostics={uniqueMessages(
              insufficientHistory,
              performanceUnavailable,
            )}
          />

          <AnalysisMetricCard
            label="Maximum drawdown"
            value={formatPercent(
              analytics.maximum_drawdown?.value ?? null,
            )}
            description="Largest peak-to-trough wealth decline in the analyzed return series."
            diagnostics={drawdownWarnings}
            footer={
              analytics.maximum_drawdown ? (
                <>
                  {analytics.maximum_drawdown.observations} return observations
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Sharpe ratio"
            value={formatRatio(analytics.sharpe?.value ?? null)}
            description="Annualized excess-return ratio using the backend risk-free-rate assumption."
            diagnostics={sharpeWarnings}
            footer={
              analytics.sharpe ? (
                <>
                  Risk-free rate{" "}
                  {formatUnsignedPercent(
                    analytics.sharpe.risk_free_rate_annual,
                  )}
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Sortino ratio"
            value={formatRatio(analytics.sortino?.value ?? null)}
            description="Annualized downside-risk ratio using the backend minimum acceptable return."
            diagnostics={sortinoWarnings}
            footer={
              analytics.sortino ? (
                <>
                  Minimum acceptable return{" "}
                  {formatUnsignedPercent(
                    analytics.sortino.minimum_acceptable_return_annual,
                  )}
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Downside deviation"
            value={formatUnsignedPercent(
              analytics.sortino?.downside_deviation ?? null,
            )}
            description="Downside deviation returned with the canonical Sortino calculation."
            diagnostics={sortinoWarnings}
          />

          <AnalysisMetricCard
            label="Beta"
            value={formatRatio(analytics.beta?.value ?? null)}
            description="Portfolio beta against the configured benchmark using aligned observations."
            diagnostics={betaWarnings}
            footer={
              analytics.provenance.benchmark ? (
                <>Benchmark {analytics.provenance.benchmark}</>
              ) : (
                <>No configured benchmark</>
              )
            }
          />

          <AnalysisMetricCard
            label="Benchmark correlation"
            value={formatRatio(
              analytics.benchmark_correlation?.value ?? null,
            )}
            description="Pearson correlation against the configured benchmark using exact-date-aligned daily returns."
            diagnostics={correlationWarnings}
            footer={
              analytics.benchmark_correlation ? (
                <>
                  {analytics.benchmark_correlation.observations} aligned
                  observations
                </>
              ) : analytics.provenance.benchmark ? (
                <>Benchmark {analytics.provenance.benchmark}</>
              ) : (
                <>No configured benchmark</>
              )
            }
          />

          <AnalysisMetricCard
            label="Portfolio observations"
            value={formatCount(analytics.observations)}
            description="Daily portfolio return observations used by the analytical service."
          />

          <AnalysisMetricCard
            label="Benchmark observations"
            value={formatCount(analytics.benchmark_observations)}
            description="Benchmark return observations available for aligned benchmark analytics."
            diagnostics={uniqueMessages(betaWarnings, correlationWarnings)}
          />
        </div>
      </section>

      <section
        className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="rolling-return-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2
              id="rolling-return-heading"
              className="text-lg font-semibold tracking-tight text-slate-950"
            >
              Rolling returns
            </h2>

            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Trailing cumulative return over an explicit number of daily return
              observations. No rolling window is assumed by the frontend or
              backend.
            </p>
          </div>

          {analytics.rolling_return_window !== null ? (
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
              {analytics.rolling_return_window}-observation window
            </span>
          ) : null}
        </div>

        {analytics.rolling_return_window === null ? (
          <div className="mt-4">
            <StatePanel
              title="Choose a rolling window"
              message="Enter a positive number of daily return observations above to request a server-calculated rolling-return series."
            />
          </div>
        ) : analytics.rolling_returns.length === 0 ? (
          <div className="mt-4">
            <StatePanel
              title="Rolling return unavailable"
              message={
                rollingWarnings[0] ??
                "The selected period does not contain enough return observations for this rolling window."
              }
            />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[28rem] border-separate border-spacing-0 text-left text-sm">
              <caption className="sr-only">
                Server-calculated rolling cumulative returns
              </caption>

              <thead>
                <tr className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  <th
                    scope="col"
                    className="border-b border-slate-200 px-3 py-2"
                  >
                    Period end
                  </th>
                  <th
                    scope="col"
                    className="border-b border-slate-200 px-3 py-2 text-right"
                  >
                    Rolling return
                  </th>
                </tr>
              </thead>

              <tbody>
                {analytics.rolling_returns.map((observation) => (
                  <tr key={observation.period_end}>
                    <td className="border-b border-slate-100 px-3 py-3 text-slate-700">
                      {formatDate(observation.period_end)}
                    </td>

                    <td className="border-b border-slate-100 px-3 py-3 text-right font-semibold tabular-nums text-slate-950">
                      {formatPercent(observation.value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section
        className="mt-5 grid gap-5 xl:grid-cols-2"
        aria-label="Current allocation and concentration"
      >
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            Current allocation context
          </h2>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            Current allocation uses the server's raw-close valuation boundary
            and is separate from historical adjusted-close return analytics.
          </p>

          {analytics.current_allocation === null ? (
            <div className="mt-4">
              <StatePanel
                title="Current allocation unavailable"
                message={
                  allocationWarnings[0] ??
                  "The analytics response did not include a current allocation result."
                }
              />
            </div>
          ) : (
            <dl className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Market value
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatCurrencyNumber(
                    analytics.current_allocation.total_market_value,
                    currency,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Cash weight
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatUnsignedPercent(
                    analytics.current_allocation.cash_weight,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Security positions
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {analytics.current_allocation.positions.length}
                </dd>
              </div>
            </dl>
          )}
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            Concentration
          </h2>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            Concentration measures come directly from the current normalized
            portfolio weights.
          </p>

          {analytics.concentration === null ? (
            <div className="mt-4">
              <StatePanel
                title="Concentration unavailable"
                message={
                  allocationWarnings[0] ??
                  "The analytics response did not include concentration measures."
                }
              />
            </div>
          ) : (
            <dl className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Largest position
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatUnsignedPercent(
                    analytics.concentration.largest_position_weight,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  {analytics.concentration.hhi_includes_cash
                    ? "HHI (includes cash)"
                    : "Security-only HHI"}
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatIndex(
                    analytics.concentration.herfindahl_hirschman_index,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Security count
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {analytics.concentration.security_position_count}
                </dd>
              </div>
            </dl>
          )}
        </div>
      </section>

      <AnalysisWarnings analytics={analytics} />

      <section
        className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="analysis-provenance-heading"
      >
        <h2
          id="analysis-provenance-heading"
          className="text-lg font-semibold tracking-tight text-slate-950"
        >
          Calculation provenance
        </h2>

        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="text-xs font-medium text-slate-500">
              As of
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {formatDate(analytics.provenance.as_of_date)}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Effective period
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.period_start} to{" "}
              {analytics.provenance.period_end}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Provider
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.data_source}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Price field
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.price_field}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Benchmark
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.benchmark ?? "Not available"}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Annualization factor
            </dt>
            <dd className="mt-1 font-medium tabular-nums text-slate-900">
              {formatCount(analytics.provenance.annualization_factor)}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Engine version
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.engine_version}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Provenance warnings
            </dt>
            <dd className="mt-1 font-medium tabular-nums text-slate-900">
              {analytics.provenance.warnings.length}
            </dd>
          </div>
        </dl>

        <div className="mt-5 border-t border-slate-100 pt-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Assumptions
          </h3>

          <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-600">
            {analytics.provenance.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}

export function PortfolioAnalysisPage() {
  const { portfolioId } = useParams<{
    portfolioId: string;
  }>();

  const [searchParams, setSearchParams] = useSearchParams();
  const portfoliosQuery = usePortfolios();

  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );

  const rangeParam = searchParams.get("range");

  const range: DashboardRange = isDashboardRange(rangeParam)
    ? rangeParam
    : "1M";

  const rollingWindowParam = searchParams.get("rollingWindow");

  const parsedRollingWindow =
    rollingWindowParam === null ? undefined : Number(rollingWindowParam);

  const rollingWindow =
    parsedRollingWindow !== undefined &&
    Number.isInteger(parsedRollingWindow) &&
    parsedRollingWindow > 0
      ? parsedRollingWindow
      : undefined;

  const request = useMemo(() => {
    if (!portfolioId || !selectedPortfolio) {
      return null;
    }

    const dates = resolveDashboardDateRange(
      range,
      selectedPortfolio.created_at,
    );

    return {
      portfolioId,
      start: dates.start,
      end: dates.end,
      rollingWindow,
    };
  }, [
    portfolioId,
    range,
    rollingWindow,
    selectedPortfolio,
  ]);

  const analyticsQuery = usePortfolioAnalytics(request);
  const analytics = analyticsQuery.data;

  const backPath = portfolioId
    ? `/portfolios/${encodeURIComponent(
        portfolioId,
      )}/dashboard?range=${encodeURIComponent(range)}`
    : "/";

  const error =
    analyticsQuery.error instanceof Error
      ? analyticsQuery.error
      : portfoliosQuery.error instanceof Error
        ? portfoliosQuery.error
        : null;

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link
            to={backPath}
            className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Portfolio dashboard
          </Link>

          <span aria-hidden="true">/</span>
          <span>Portfolio analysis</span>
        </div>

        <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          {selectedPortfolio?.name ?? "Portfolio analysis"}
        </h1>
      </div>

      <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
        Range {range === "ALL" ? "All" : range}
      </span>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <section
        className="mb-5 flex flex-wrap items-end justify-between gap-4"
        aria-label="Analysis period controls"
      >
        <div>
          <p className="text-sm font-medium text-slate-500">
            Requested period
          </p>

          <p className="mt-0.5 text-sm text-slate-700">
            {request
              ? `${request.start} to ${request.end} (end exclusive)`
              : "Waiting for portfolio context"}
          </p>
        </div>

        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();

            const form = new FormData(event.currentTarget);
            const rawValue = String(
              form.get("rollingWindow") ?? "",
            ).trim();

            const next = new URLSearchParams(searchParams);

            if (!rawValue) {
              next.delete("rollingWindow");
              setSearchParams(next);
              return;
            }

            const value = Number(rawValue);

            if (!Number.isInteger(value) || value <= 0) {
              return;
            }

            next.set("rollingWindow", String(value));
            setSearchParams(next);
          }}
        >
          <label className="block text-xs font-medium text-slate-600">
            Rolling window
            <input
              key={rollingWindowParam ?? "none"}
              name="rollingWindow"
              type="number"
              min={1}
              step={1}
              defaultValue={rollingWindowParam ?? ""}
              placeholder="e.g. 21"
              className="mt-1 block w-32 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </label>

          <button
            type="submit"
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none transition hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Apply window
          </button>
        </form>

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

      {!portfoliosQuery.isPending &&
      portfoliosQuery.data &&
      !selectedPortfolio ? (
        <StatePanel
          title="Portfolio not found"
          message="This portfolio is not available in the authenticated account scope."
          tone="error"
          action={
            <Link
              to="/"
              className="inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Choose a portfolio
            </Link>
          }
        />
      ) : portfoliosQuery.isPending ||
        (analyticsQuery.isPending && analytics === undefined) ? (
        <AnalysisSkeleton />
      ) : error !== null && analytics === undefined ? (
        <StatePanel
          title={
            error instanceof ApiError && error.status === 403
              ? "Portfolio access denied"
              : error instanceof ApiError && error.status === 404
                ? "Portfolio not found"
                : error instanceof ApiError &&
                    error.status === 400 &&
                    error.code === "INSUFFICIENT_ANALYTICS_PERIOD"
                  ? "Analysis period is insufficient"
                  : "Portfolio analysis could not load"
          }
          message={error.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => {
                void portfoliosQuery.refetch();

                if (request !== null) {
                  void analyticsQuery.refetch();
                }
              }}
              className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Retry
            </button>
          }
        />
      ) : analytics === undefined ? (
        <StatePanel
          title="No portfolio analysis"
          message="No analytical result is available for this portfolio and selected period."
        />
      ) : (
        <div className="relative">
          {error !== null ? (
            <div
              className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
              role="status"
            >
              Refresh failed. Showing the most recent successful analytical
              result.
            </div>
          ) : null}

          {analyticsQuery.isFetching ? (
            <div
              className="mb-4 inline-flex rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800"
              role="status"
              aria-live="polite"
            >
              Refreshing analysis…
            </div>
          ) : null}

          <AnalysisContent
            analytics={analytics}
            currency={selectedPortfolio?.base_currency ?? "USD"}
          />
        </div>
      )}
    </DashboardShell>
  );
}