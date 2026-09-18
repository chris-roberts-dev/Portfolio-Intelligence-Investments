import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router";

import { ApiError } from "../api/client";
import { RebalanceValueComparisonChart } from "../components/charts/RebalanceValueComparisonChart";
import { DomainPageHeader } from "../components/ui/DomainPageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
  humanizeCode,
} from "../features/dashboard/formatting";
import {
  policyByName,
  successfulPortfolioOptimizationRuns,
  targetAllocationsForPortfolio,
  targetRequestFromOptimizationRun,
  tradeLines,
} from "../features/rebalancing/rebalancingTransforms";
import { useOptimizationRuns } from "../hooks/useOptimizationData";
import { useAssetCatalog, usePortfolios } from "../hooks/usePortfolioData";
import {
  useCreateHistoricalRebalanceComparison,
  useCreateRebalanceSimulation,
  useCreateTargetAllocation,
  useHistoricalRebalanceComparisons,
  useTargetAllocations,
} from "../hooks/useRebalancingData";
import { DashboardShell } from "../layouts/DashboardShell";
import type { OptimizationRun } from "../types/optimization";
import type {
  HistoricalRebalanceComparison,
  HistoricalRebalancePolicyResult,
  RebalanceLine,
  RebalancingWarning,
} from "../types/rebalancing";

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultDates(): { start: string; end: string } {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
  return { start: formatLocalDate(start), end: formatLocalDate(end) };
}

function formatNumber(value: number, digits = 2): string {
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatPercentagePoints(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not available";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, 2)} pp`;
}

function policyComparisonSentence(
  policy: HistoricalRebalancePolicyResult | null,
): string | null {
  if (policy === null) {
    return null;
  }

  const difference = policy.summary.return_difference_pp_vs_actual;
  if (difference === null || difference === undefined) {
    return null;
  }
  const label = `${policyLabel(policy.name)} rebalancing`;
  if (difference > 0) {
    return `${label} outperformed the actual portfolio by ${formatNumber(Math.abs(difference), 2)} pp.`;
  }
  if (difference < 0) {
    return `${label} underperformed the actual portfolio by ${formatNumber(Math.abs(difference), 2)} pp.`;
  }
  return `${label} matched the actual portfolio return.`;
}

function policyLabel(name: string): string {
  switch (name) {
    case "annual":
      return "Annual";
    case "quarterly":
      return "Quarterly";
    case "monthly":
      return "Monthly";
    case "threshold":
      return "Drift threshold";
    default:
      return humanizeCode(name) ?? name;
  }
}

function errorCopy(error: Error): { title: string; message: string } {
  if (!(error instanceof ApiError)) {
    return { title: "Rebalancing request failed", message: error.message };
  }

  if (error.code === "INSUFFICIENT_MARKET_DATA" || error.code === "INSUFFICIENT_DATA") {
    return {
      title: "Insufficient historical data",
      message: error.message,
    };
  }
  if (error.status === 404) {
    return { title: "Rebalancing resource not found", message: error.message };
  }
  if (error.status === 503) {
    return { title: "Market-data dependency unavailable", message: error.message };
  }
  if (error.status === 400) {
    return { title: "Rebalancing configuration is invalid", message: error.message };
  }
  return { title: "Rebalancing request failed", message: error.message };
}

function warningPanel(warnings: readonly RebalancingWarning[]) {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <div
      className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"
      role="status"
      aria-label="Rebalancing warnings"
    >
      <p className="font-semibold">Review these assumptions and data warnings</p>
      <ul className="mt-2 space-y-2">
        {warnings.map((warning, index) => (
          <li key={`${warning.code}-${index}`}>
            <span className="font-semibold">{humanizeCode(warning.code) ?? warning.code}:</span>{" "}
            {warning.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TargetCreationPanel({
  portfolioId,
  runs,
  onCreated,
}: {
  portfolioId: string;
  runs: OptimizationRun[];
  onCreated: (targetId: string) => void;
}) {
  const createTarget = useCreateTargetAllocation();
  const [runId, setRunId] = useState("");
  const [name, setName] = useState("Optimization target");
  const selectedRun = runs.find((run) => run.id === runId) ?? null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedRun === null || !name.trim()) {
      return;
    }
    const request = targetRequestFromOptimizationRun(selectedRun, name);
    if (request === null) {
      return;
    }
    try {
      const target = await createTarget.mutateAsync(request);
      onCreated(target.id);
    } catch {
      // Mutation state renders the stable API error without an unhandled promise rejection.
    }
  }

  const error = createTarget.error instanceof Error ? errorCopy(createTarget.error) : null;

  return (
    <section className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">Create target from optimization</h2>
      <p className="mt-1 text-sm leading-6 text-slate-600">
        Successful portfolio-derived Allocation Lab results can be saved as immutable target
        allocations. The optimizer weights are sent unchanged to the target-allocation API.
      </p>

      {runs.length === 0 ? (
        <StatePanel
          title="No successful portfolio optimization run"
          message="Run a portfolio-derived optimization first, then return here to save its weights as a target allocation."
          action={
            <Link
              to={`/portfolios/${encodeURIComponent(portfolioId)}/allocation-lab`}
              className="font-semibold text-blue-700 underline underline-offset-4"
            >
              Open Allocation Lab
            </Link>
          }
        />
      ) : (
        <form className="mt-4 grid gap-4" onSubmit={submit}>
          <label className="text-xs font-semibold text-slate-700">
            Successful optimization run
            <select
              aria-label="Successful optimization run"
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <option value="">Select run</option>
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.method.replaceAll("_", " ")} · {run.provenance.period_start} to{" "}
                  {run.provenance.period_end_exclusive}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700">
            Target name
            <input
              aria-label="Target name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </label>
          <button
            type="submit"
            disabled={selectedRun === null || !name.trim() || createTarget.isPending}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
          >
            {createTarget.isPending ? "Saving target…" : "Save target"}
          </button>
        </form>
      )}

      {error ? (
        <div className="mt-4">
          <StatePanel title={error.title} message={error.message} tone="error" />
        </div>
      ) : null}
    </section>
  );
}

function CurrentSimulationPanel({
  lines,
  currency,
  assetLabel,
}: {
  lines: readonly RebalanceLine[];
  currency: string;
  assetLabel: (assetId: string | null, isCash: boolean) => string;
}) {
  const trades = tradeLines(lines);
  return (
    <div className="mt-5 space-y-5">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] border-collapse text-left text-sm">
          <caption className="sr-only">Current allocation, target allocation, drift, and simulated trade notionals</caption>
          <thead>
            <tr className="border-b border-slate-200 text-xs text-slate-500">
              <th className="py-2 pr-4 font-semibold">Asset</th>
              <th className="py-2 pr-4 font-semibold">Current</th>
              <th className="py-2 pr-4 font-semibold">Target</th>
              <th className="py-2 pr-4 font-semibold">Absolute drift</th>
              <th className="py-2 pr-4 font-semibold">Relative drift</th>
              <th className="py-2 pr-4 font-semibold">Simulated trade</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.asset_id ?? "cash"} className="border-b border-slate-100">
                <th className="py-3 pr-4 font-semibold text-slate-950">
                  {assetLabel(line.asset_id, line.is_cash)}
                </th>
                <td className="py-3 pr-4 tabular-nums">{formatPercent(line.current_weight)}</td>
                <td className="py-3 pr-4 tabular-nums">{formatPercent(line.target_weight)}</td>
                <td className="py-3 pr-4 tabular-nums">{formatPercent(line.absolute_drift)}</td>
                <td className="py-3 pr-4 tabular-nums">{formatPercent(line.relative_drift)}</td>
                <td className="py-3 pr-4 tabular-nums">
                  {line.is_cash
                    ? `Cash adjustment ${formatCurrency(String(Math.abs(line.trade_notional)), currency)}`
                    : line.direction === "NONE"
                      ? "No trade"
                      : `${line.direction} ${formatCurrency(String(Math.abs(line.trade_notional)), currency)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-sm text-slate-600">
        {trades.length === 0
          ? "The current allocation already matches the target within the engine tolerance."
          : `${trades.length} simulated trade${trades.length === 1 ? "" : "s"} would move the current portfolio toward this target. These are model outputs, not orders.`}
      </p>
    </div>
  );
}

function ActualPortfolioBaselineSummary({
  comparison,
  currency,
}: {
  comparison: HistoricalRebalanceComparison;
  currency: string;
}) {
  const actual = comparison.result.actual_portfolio;

  if (!actual?.available) {
    return (
      <StatePanel
        title="Actual portfolio baseline unavailable"
        message="The hypothetical rebalancing policies are available, but an exact same-period actual portfolio TWR baseline could not be calculated. Review the comparison warnings for the missing valuation evidence."
      />
    );
  }

  return (
    <section
      className="rounded-xl border border-slate-200 bg-slate-50 p-4"
      aria-label="Actual portfolio comparison baseline"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Actual portfolio baseline
          </p>
          <p className="mt-1 text-sm text-slate-700">
            Canonical daily time-weighted return over the exact aligned comparison period.
          </p>
        </div>
        <span className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
          {actual.period_start} to {actual.period_end}
        </span>
      </div>
      <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-xs text-slate-500">Actual start value</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-950">
            {formatCurrency(
              actual.starting_portfolio_value === null
                ? null
                : String(actual.starting_portfolio_value),
              currency,
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Actual end value</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-950">
            {formatCurrency(
              actual.ending_portfolio_value === null
                ? null
                : String(actual.ending_portfolio_value),
              currency,
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Same-period actual TWR</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-950">
            {formatPercent(actual.cumulative_return)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Growth of $100</dt>
          <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-950">
            {actual.growth_of_100_end === null || actual.growth_of_100_end === undefined
              ? "Not available"
              : formatCurrency(String(actual.growth_of_100_end), currency)}
          </dd>
        </div>
      </dl>
      <p className="mt-3 text-xs leading-5 text-slate-600">
        Actual start/end values are account valuations. Growth of $100 is a normalized
        return index used only to compare paths. The TWR shown here is not a since-inception
        return unless this comparison begins at portfolio inception.
      </p>
    </section>
  );
}

function PolicySummaryTable({
  comparison,
  currency,
  selectedPolicy,
  onSelectPolicy,
}: {
  comparison: HistoricalRebalanceComparison;
  currency: string;
  selectedPolicy: string;
  onSelectPolicy: (name: string) => void;
}) {
  const actual = comparison.result.actual_portfolio;

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1120px] border-collapse text-left text-sm">
        <caption className="sr-only">
          Actual portfolio and historical rebalancing policy comparison
        </caption>
        <thead>
          <tr className="border-b border-slate-200 text-xs text-slate-500">
            <th className="py-2 pr-4 font-semibold">Policy</th>
            <th className="py-2 pr-4 font-semibold">Ending value</th>
            <th className="py-2 pr-4 font-semibold">Period return</th>
            <th className="py-2 pr-4 font-semibold">Vs actual</th>
            <th className="py-2 pr-4 font-semibold">Rebalances</th>
            <th className="py-2 pr-4 font-semibold">Trades</th>
            <th className="py-2 pr-4 font-semibold">Turnover</th>
            <th className="py-2 pr-4 font-semibold">Max drift</th>
            <th className="py-2 pr-4 font-semibold">Total costs</th>
          </tr>
        </thead>
        <tbody>
          {actual ? (
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="py-3 pr-4 font-semibold text-slate-950">Actual portfolio</th>
              <td className="py-3 pr-4 tabular-nums">
                {formatCurrency(
                  actual.ending_portfolio_value === null
                    ? null
                    : String(actual.ending_portfolio_value),
                  currency,
                )}
              </td>
              <td className="py-3 pr-4 tabular-nums">
                {formatPercent(actual.cumulative_return)}
              </td>
              <td className="py-3 pr-4 font-semibold text-slate-700">Baseline</td>
              <td className="py-3 pr-4 text-slate-500">—</td>
              <td className="py-3 pr-4 text-slate-500">—</td>
              <td className="py-3 pr-4 text-slate-500">—</td>
              <td className="py-3 pr-4 text-slate-500">—</td>
              <td className="py-3 pr-4 text-slate-500">—</td>
            </tr>
          ) : null}
          {comparison.result.policies.map((policy) => (
            <tr key={policy.name} className="border-b border-slate-100">
              <th className="py-3 pr-4">
                <button
                  type="button"
                  aria-pressed={selectedPolicy === policy.name}
                  onClick={() => onSelectPolicy(policy.name)}
                  className="font-semibold text-blue-700 underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  {policyLabel(policy.name)}
                </button>
              </th>
              <td className="py-3 pr-4 tabular-nums">
                {formatCurrency(String(policy.summary.ending_value), currency)}
              </td>
              <td className="py-3 pr-4 tabular-nums">
                {formatPercent(policy.summary.cumulative_return)}
              </td>
              <td className="py-3 pr-4 tabular-nums font-semibold">
                {formatPercentagePoints(policy.summary.return_difference_pp_vs_actual)}
              </td>
              <td className="py-3 pr-4 tabular-nums">{policy.summary.rebalance_count}</td>
              <td className="py-3 pr-4 tabular-nums">{policy.summary.trade_count}</td>
              <td className="py-3 pr-4 tabular-nums">
                {formatNumber(policy.summary.turnover, 3)}
              </td>
              <td className="py-3 pr-4 tabular-nums">
                {formatPercent(policy.summary.maximum_absolute_drift)}
              </td>
              <td className="py-3 pr-4 tabular-nums">
                {formatCurrency(String(policy.summary.total_cost), currency)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs leading-5 text-slate-500">
        Percentage-point differences compare each hypothetical policy return with the actual
        portfolio's canonical TWR over this same aligned period. Ending dollar values are
        account/simulation values and are not used to calculate the percentage-point comparison.
      </p>
    </div>
  );
}

function PolicyDetail({
  policy,
  currency,
  assetLabel,
}: {
  policy: HistoricalRebalancePolicyResult;
  currency: string;
  assetLabel: (assetId: string | null, isCash: boolean) => string;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-semibold text-slate-950">{policyLabel(policy.name)} event detail</h2>
      <p className="mt-1 text-sm text-slate-600">
        Decision dates use observable end-of-day state. Execution dates are the later aligned observations used for simulated fills.
      </p>

      {policy.events.length === 0 ? (
        <div className="mt-4">
          <StatePanel
            title="No rebalance events in this period"
            message="This rule did not trigger an executable rebalance over the aligned historical period."
          />
        </div>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[900px] border-collapse text-left text-sm">
            <caption className="sr-only">Rebalance decision and execution events</caption>
            <thead>
              <tr className="border-b border-slate-200 text-xs text-slate-500">
                <th className="py-2 pr-4 font-semibold">Trigger</th>
                <th className="py-2 pr-4 font-semibold">Decision date</th>
                <th className="py-2 pr-4 font-semibold">Execution date</th>
                <th className="py-2 pr-4 font-semibold">Trades</th>
                <th className="py-2 pr-4 font-semibold">Turnover</th>
                <th className="py-2 pr-4 font-semibold">Commission / slippage</th>
              </tr>
            </thead>
            <tbody>
              {policy.events.map((event, index) => (
                <tr key={`${event.decision_date}-${event.execution_date}-${index}`} className="border-b border-slate-100">
                  <td className="py-3 pr-4">{humanizeCode(event.trigger) ?? event.trigger}</td>
                  <td className="py-3 pr-4 font-medium">{formatDate(event.decision_date)}</td>
                  <td className="py-3 pr-4 font-medium text-blue-800">{formatDate(event.execution_date)}</td>
                  <td className="py-3 pr-4 tabular-nums">{event.trades.length}</td>
                  <td className="py-3 pr-4 tabular-nums">{formatNumber(event.turnover, 3)}</td>
                  <td className="py-3 pr-4 tabular-nums">{formatCurrency(String(event.commission_cost), currency)} / {formatCurrency(String(event.slippage_cost), currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {policy.events.some((event) => event.trades.length > 0) ? (
        <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
          <summary className="cursor-pointer font-semibold text-slate-800">View simulated fills</summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[880px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-4 font-semibold">Execution date</th>
                  <th className="py-2 pr-4 font-semibold">Asset</th>
                  <th className="py-2 pr-4 font-semibold">Direction</th>
                  <th className="py-2 pr-4 font-semibold">Quantity</th>
                  <th className="py-2 pr-4 font-semibold">Reference price</th>
                  <th className="py-2 pr-4 font-semibold">Fill price</th>
                  <th className="py-2 pr-4 font-semibold">Notional</th>
                </tr>
              </thead>
              <tbody>
                {policy.events.flatMap((event) =>
                  event.trades.map((trade, index) => (
                    <tr key={`${event.execution_date}-${trade.asset_id}-${index}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4">{formatDate(event.execution_date)}</td>
                      <td className="py-2 pr-4 font-semibold">{assetLabel(trade.asset_id, false)}</td>
                      <td className="py-2 pr-4">{trade.direction}</td>
                      <td className="py-2 pr-4 tabular-nums">{formatNumber(trade.quantity, 4)}</td>
                      <td className="py-2 pr-4 tabular-nums">{formatCurrency(String(trade.reference_price), currency)}</td>
                      <td className="py-2 pr-4 tabular-nums">{formatCurrency(String(trade.fill_price), currency)}</td>
                      <td className="py-2 pr-4 tabular-nums">{formatCurrency(String(trade.fill_notional), currency)}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}

      <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-semibold text-slate-800">View allocation and drift history</summary>
        <div className="mt-3 max-h-[32rem] overflow-auto">
          <table className="w-full min-w-[760px] border-collapse text-left text-xs">
            <thead className="sticky top-0 bg-slate-50">
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">Date</th>
                <th className="py-2 pr-4 font-semibold">Asset</th>
                <th className="py-2 pr-4 font-semibold">Weight</th>
                <th className="py-2 pr-4 font-semibold">Target</th>
                <th className="py-2 pr-4 font-semibold">Absolute drift</th>
                <th className="py-2 pr-4 font-semibold">Value</th>
              </tr>
            </thead>
            <tbody>
              {policy.snapshots.flatMap((snapshot) =>
                snapshot.lines.map((line) => (
                  <tr key={`${snapshot.trade_date}-${line.asset_id ?? "cash"}`} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{formatDate(snapshot.trade_date)}</td>
                    <td className="py-2 pr-4 font-semibold">{assetLabel(line.asset_id, line.is_cash)}</td>
                    <td className="py-2 pr-4 tabular-nums">{formatPercent(line.weight)}</td>
                    <td className="py-2 pr-4 tabular-nums">{formatPercent(line.target_weight)}</td>
                    <td className="py-2 pr-4 tabular-nums">{formatPercent(line.absolute_drift)}</td>
                    <td className="py-2 pr-4 tabular-nums">{formatCurrency(String(line.market_value), currency)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </details>

      {policy.warnings.length > 0 ? <div className="mt-4">{warningPanel(policy.warnings)}</div> : null}
    </section>
  );
}

export function RebalancingLabPage() {
  const { portfolioId: routePortfolioId } = useParams<{ portfolioId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const defaults = useMemo(defaultDates, []);
  const queryPortfolioId = searchParams.get("portfolio");
  const requestedTargetId = searchParams.get("target");

  const portfoliosQuery = usePortfolios();
  const targetsQuery = useTargetAllocations();
  const runsQuery = useOptimizationRuns();
  const assetsQuery = useAssetCatalog();
  const comparisonsQuery = useHistoricalRebalanceComparisons();
  const createSimulation = useCreateRebalanceSimulation();
  const createComparison = useCreateHistoricalRebalanceComparison();

  const [portfolioId, setPortfolioId] = useState(routePortfolioId ?? queryPortfolioId ?? "");
  const [targetId, setTargetId] = useState(requestedTargetId ?? "");
  const [periodStart, setPeriodStart] = useState(defaults.start);
  const [periodEnd, setPeriodEnd] = useState(defaults.end);
  const [threshold, setThreshold] = useState("0.05");
  const [commissionRate, setCommissionRate] = useState("0");
  const [slippageRate, setSlippageRate] = useState("0");
  const [includeMonthly, setIncludeMonthly] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState("annual");
  const [openedComparison, setOpenedComparison] = useState<HistoricalRebalanceComparison | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const portfolios = portfoliosQuery.data ?? [];
  const selectedPortfolio = portfolios.find((portfolio) => portfolio.id === portfolioId) ?? null;
  const targets = useMemo(
    () => targetAllocationsForPortfolio(targetsQuery.data ?? [], portfolioId),
    [portfolioId, targetsQuery.data],
  );
  const successfulRuns = useMemo(
    () => successfulPortfolioOptimizationRuns(runsQuery.data ?? [], portfolioId),
    [portfolioId, runsQuery.data],
  );
  const historicalForPortfolio = useMemo(
    () =>
      (comparisonsQuery.data ?? []).filter(
        (comparison) => comparison.portfolio_id === portfolioId,
      ),
    [comparisonsQuery.data, portfolioId],
  );
  const activeComparison = openedComparison ?? createComparison.data ?? null;
  const activePolicy = policyByName(activeComparison, selectedPolicy);
  const activeComparisonSentence = policyComparisonSentence(activePolicy);

  const assetLabels = useMemo(
    () => new Map((assetsQuery.data ?? []).map((asset) => [asset.id, asset.symbol] as const)),
    [assetsQuery.data],
  );
  const assetLabel = (assetId: string | null, isCash: boolean) =>
    isCash || assetId === null ? "Cash" : assetLabels.get(assetId) ?? assetId;

  useEffect(() => {
    if (portfolioId && targets.length > 0 && !targets.some((target) => target.id === targetId)) {
      setTargetId(targets[0]?.id ?? "");
    }
    if (targets.length === 0 && targetId) {
      setTargetId("");
    }
  }, [portfolioId, targetId, targets]);

  useEffect(() => {
    if (activeComparison && !activeComparison.result.policies.some((policy) => policy.name === selectedPolicy)) {
      setSelectedPolicy(activeComparison.result.policies[0]?.name ?? "annual");
    }
  }, [activeComparison, selectedPolicy]);

  function updatePortfolio(nextPortfolioId: string) {
    setPortfolioId(nextPortfolioId);
    setTargetId("");
    setOpenedComparison(null);
    createSimulation.reset();
    createComparison.reset();
    const next = new URLSearchParams(searchParams);
    if (nextPortfolioId) {
      next.set("portfolio", nextPortfolioId);
    } else {
      next.delete("portfolio");
    }
    next.delete("target");
    setSearchParams(next, { replace: true });
  }

  function updateTarget(nextTargetId: string) {
    setTargetId(nextTargetId);
    setOpenedComparison(null);
    createSimulation.reset();
    createComparison.reset();
    const next = new URLSearchParams(searchParams);
    if (nextTargetId) {
      next.set("target", nextTargetId);
    } else {
      next.delete("target");
    }
    setSearchParams(next, { replace: true });
  }

  async function runCurrentSimulation() {
    setFormError(null);
    const parsedThreshold = Number(threshold);
    if (!portfolioId || !targetId || !Number.isFinite(parsedThreshold) || parsedThreshold < 0 || parsedThreshold > 1) {
      setFormError("Select a portfolio and target and enter a drift threshold between 0 and 1.");
      return;
    }
    try {
      await createSimulation.mutateAsync({
        portfolio_id: portfolioId,
        target_allocation_id: targetId,
        drift_threshold: parsedThreshold,
      });
    } catch {
      // Mutation state renders the stable API error.
    }
  }

  async function runHistoricalComparison(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const parsedThreshold = Number(threshold);
    const parsedCommission = Number(commissionRate);
    const parsedSlippage = Number(slippageRate);
    if (!portfolioId || !targetId) {
      setFormError("Select a portfolio and target allocation first.");
      return;
    }
    if (!periodStart || !periodEnd || periodStart >= periodEnd) {
      setFormError("Historical comparison end date must be later than the start date.");
      return;
    }
    if (![parsedThreshold, parsedCommission, parsedSlippage].every((value) => Number.isFinite(value) && value >= 0 && value <= 1)) {
      setFormError("Threshold, commission, and slippage values must be between 0 and 1.");
      return;
    }

    try {
      const comparison = await createComparison.mutateAsync({
        portfolio_id: portfolioId,
        target_allocation_id: targetId,
        period_start: periodStart,
        period_end: periodEnd,
        drift_threshold: parsedThreshold,
        commission_rate: parsedCommission,
        slippage_rate: parsedSlippage,
        include_monthly: includeMonthly,
      });
      setOpenedComparison(comparison);
      setSelectedPolicy(comparison.result.policies[0]?.name ?? "annual");
    } catch {
      // Mutation state renders insufficient-data, validation, or dependency errors.
    }
  }

  const loading = portfoliosQuery.isPending || targetsQuery.isPending || runsQuery.isPending || assetsQuery.isPending;
  const queryError = portfoliosQuery.error ?? targetsQuery.error ?? runsQuery.error ?? assetsQuery.error;
  const simulationError = createSimulation.error instanceof Error ? errorCopy(createSimulation.error) : null;
  const comparisonError = createComparison.error instanceof Error ? errorCopy(createComparison.error) : null;

  const header = (
    <DomainPageHeader
      eyebrow="Portfolio simulation"
      title="Rebalancing Lab"
      description="Compare current allocation with a saved target, simulate transparent trade notionals, and evaluate deterministic annual, quarterly, and drift-threshold rebalancing over an explicit historical period."
      actions={
        portfolioId ? (
          <div className="flex flex-wrap gap-3">
            <Link
              to={`/portfolios/${encodeURIComponent(portfolioId)}/allocation-lab`}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Allocation Lab
            </Link>
            <Link
              to={`/portfolios/${encodeURIComponent(portfolioId)}/dashboard`}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Portfolio dashboard
            </Link>
          </div>
        ) : null
      }
    />
  );

  return (
    <DashboardShell header={header}>
      <main className="mx-auto w-full max-w-[1800px] space-y-6 px-3 pb-10 sm:px-4 lg:px-5 xl:px-6">
        {loading ? (
          <div aria-label="Loading Rebalancing Lab" className="space-y-5">
            <Skeleton className="h-36 w-full rounded-2xl" />
            <Skeleton className="h-72 w-full rounded-2xl" />
          </div>
        ) : queryError instanceof Error ? (
          <StatePanel title="Rebalancing Lab data could not be loaded" message={queryError.message} tone="error" />
        ) : portfolios.length === 0 ? (
          <StatePanel
            title="Create a portfolio first"
            message="Rebalancing compares an owned portfolio with a target allocation, so an owned portfolio is required."
            action={<Link to="/portfolios" className="font-semibold text-blue-700 underline underline-offset-4">Open portfolios</Link>}
          />
        ) : (
          <>
            <div className="grid gap-5 xl:grid-cols-4" aria-label="Rebalancing workflow controls">
            <section className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-950">Portfolio and target</h2>
              <div className="mt-4 grid gap-4">
                <label className="text-xs font-semibold text-slate-700">
                  Owned portfolio
                  <select
                    aria-label="Owned portfolio"
                    value={portfolioId}
                    onChange={(event) => updatePortfolio(event.target.value)}
                    className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    <option value="">Select portfolio</option>
                    {portfolios.map((portfolio) => <option key={portfolio.id} value={portfolio.id}>{portfolio.name}</option>)}
                  </select>
                </label>
                <label className="text-xs font-semibold text-slate-700">
                  Saved target allocation
                  <select
                    aria-label="Saved target allocation"
                    value={targetId}
                    onChange={(event) => updateTarget(event.target.value)}
                    disabled={!portfolioId || targets.length === 0}
                    className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:bg-slate-100"
                  >
                    <option value="">Select target</option>
                    {targets.map((target) => <option key={target.id} value={target.id}>{target.name}</option>)}
                  </select>
                </label>
              </div>
              {portfolioId && targets.length === 0 ? (
                <p className="mt-3 text-sm text-slate-600">No saved targets exist for this portfolio yet. Create one from a successful optimization run below.</p>
              ) : null}
            </section>

            {portfolioId ? (
              <TargetCreationPanel
                portfolioId={portfolioId}
                runs={successfulRuns}
                onCreated={(createdTargetId) => updateTarget(createdTargetId)}
              />
            ) : null}

            <section className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">Current drift and simulated rebalance</h2>
                  <p className="mt-1 text-sm text-slate-600">Uses the server's current valuation and target-allocation engine. Trade notionals are simulations, not orders.</p>
                </div>
                <button
                  type="button"
                  onClick={() => void runCurrentSimulation()}
                  disabled={!portfolioId || !targetId || createSimulation.isPending}
                  className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white outline-none hover:bg-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
                >
                  {createSimulation.isPending ? "Simulating…" : "Simulate current rebalance"}
                </button>
              </div>

              {simulationError ? <div className="mt-4"><StatePanel title={simulationError.title} message={simulationError.message} tone="error" /></div> : null}
              {createSimulation.data ? (
                <dl className="mt-5 grid grid-cols-2 gap-4">
                  <div><dt className="text-xs text-slate-500">Investable value</dt><dd className="mt-1 text-base font-semibold tabular-nums">{formatCurrency(String(createSimulation.data.result.total_investable_value), selectedPortfolio?.base_currency ?? "USD")}</dd></div>
                  <div><dt className="text-xs text-slate-500">Threshold</dt><dd className="mt-1 text-base font-semibold tabular-nums">{formatPercent(createSimulation.data.result.rules.threshold)}</dd></div>
                  <div><dt className="text-xs text-slate-500">Status</dt><dd className="mt-1 text-sm font-semibold">{createSimulation.data.result.rules.threshold_triggered ? "Triggered" : "Within threshold"}</dd></div>
                  <div><dt className="text-xs text-slate-500">Valuation</dt><dd className="mt-1 text-sm font-semibold">{createSimulation.data.provider} · {createSimulation.data.price_field}</dd></div>
                </dl>
              ) : (
                <p className="mt-4 text-sm leading-6 text-slate-600">Run the current simulation to calculate authoritative drift and simulated trade notionals.</p>
              )}
            </section>

            <form className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={(event) => void runHistoricalComparison(event)}>
              <h2 className="text-lg font-semibold text-slate-950">Historical rule comparison</h2>
              <p className="mt-1 text-sm text-slate-600">Annual, quarterly, and absolute drift-threshold policies share the same initial state, aligned adjusted-close history, costs, and target allocation.</p>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <label className="text-xs font-semibold text-slate-700">Period start<input aria-label="Historical period start" type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500" /></label>
                <label className="text-xs font-semibold text-slate-700">Period end<input aria-label="Historical period end" type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500" /></label>
                <label className="text-xs font-semibold text-slate-700">Drift threshold<input aria-label="Absolute drift threshold" type="number" min="0" max="1" step="0.001" value={threshold} onChange={(event) => setThreshold(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500" /></label>
                <label className="text-xs font-semibold text-slate-700">Commission rate<input aria-label="Commission rate" type="number" min="0" max="1" step="0.0001" value={commissionRate} onChange={(event) => setCommissionRate(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500" /></label>
                <label className="text-xs font-semibold text-slate-700">Slippage rate<input aria-label="Slippage rate" type="number" min="0" max="1" step="0.0001" value={slippageRate} onChange={(event) => setSlippageRate(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500" /></label>
                <label className="col-span-2 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700"><input type="checkbox" checked={includeMonthly} onChange={(event) => setIncludeMonthly(event.target.checked)} />Include monthly</label>
              </div>
              {formError ? <p className="mt-4 text-sm font-medium text-rose-700" role="alert">{formError}</p> : null}
              <button type="submit" disabled={!portfolioId || !targetId || createComparison.isPending} className="mt-5 w-full rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white outline-none hover:bg-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50">{createComparison.isPending ? "Running historical comparison…" : "Run historical comparison"}</button>
              {comparisonError ? <div className="mt-4"><StatePanel title={comparisonError.title} message={comparisonError.message} tone="error" /></div> : null}
            </form>
            </div>

            {createSimulation.data ? (
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-label="Current rebalance simulation detail">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Current simulation</p>
                    <h2 className="mt-1 text-lg font-semibold text-slate-950">Current allocation, drift, and simulated trades</h2>
                  </div>
                  <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">Simulation · not an order</span>
                </div>
                <CurrentSimulationPanel lines={createSimulation.data.result.lines} currency={selectedPortfolio?.base_currency ?? "USD"} assetLabel={assetLabel} />
                {createSimulation.data.warnings.length > 0 ? <div className="mt-4">{warningPanel(createSimulation.data.warnings)}</div> : null}
              </section>
            ) : null}

            {historicalForPortfolio.length > 0 ? (
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <h2 className="text-lg font-semibold text-slate-950">Saved comparisons</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {historicalForPortfolio.slice(0, 8).map((comparison) => (
                    <button key={comparison.id} type="button" onClick={() => { setOpenedComparison(comparison); setSelectedPolicy(comparison.result.policies[0]?.name ?? "annual"); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500">{comparison.period_start} → {comparison.period_end}</button>
                  ))}
                </div>
              </section>
            ) : null}

            {activeComparison ? (
              <>
                {warningPanel(activeComparison.warnings)}
                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-label="Historical rebalancing comparison results">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">Persisted comparison</p><h2 className="mt-1 text-lg font-semibold text-slate-950">Policy outcomes</h2><p className="mt-1 text-sm text-slate-600">{activeComparison.result.period_start} to {activeComparison.result.period_end} aligned market history</p></div>
                    <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">Historical simulation · not investment advice</span>
                  </div>
                  {activeComparisonSentence ? (
                    <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950" role="status">
                      <p className="font-semibold">{activeComparisonSentence}</p>
                      <p className="mt-1 text-blue-900">Percentage-point differences are calculated by the backend from cumulative policy return minus actual portfolio TWR.</p>
                    </div>
                  ) : null}
                  <div className="mt-5">
                    <ActualPortfolioBaselineSummary
                      comparison={activeComparison}
                      currency={selectedPortfolio?.base_currency ?? "USD"}
                    />
                  </div>
                  <div className="mt-5"><PolicySummaryTable comparison={activeComparison} currency={selectedPortfolio?.base_currency ?? "USD"} selectedPolicy={activePolicy?.name ?? selectedPolicy} onSelectPolicy={setSelectedPolicy} /></div>
                  <div className="mt-6"><h3 className="text-sm font-semibold text-slate-950">Growth of $100</h3><p className="mt-1 text-sm text-slate-600">All lines are normalized to 100 at the first aligned observation. The actual line follows canonical same-period TWR; hypothetical lines follow persisted simulated portfolio values.</p><div className="mt-3"><RebalanceValueComparisonChart comparison={activeComparison} currency={selectedPortfolio?.base_currency ?? "USD"} /></div></div>
                </section>

                <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-label="Historical comparison assumptions and provenance">
                  <h2 className="text-lg font-semibold text-slate-950">Assumptions and provenance</h2>
                  <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                    <div><dt className="text-xs text-slate-500">Price convention</dt><dd className="mt-1 font-semibold text-slate-900">{activeComparison.result.assumptions.price_field}</dd></div>
                    <div><dt className="text-xs text-slate-500">Execution timing</dt><dd className="mt-1 font-semibold text-slate-900">Decision at t · execute at next aligned observation</dd></div>
                    <div><dt className="text-xs text-slate-500">Provider</dt><dd className="mt-1 font-semibold text-slate-900">{activeComparison.result.provenance.provider}</dd></div>
                    <div><dt className="text-xs text-slate-500">Retrieved</dt><dd className="mt-1 font-semibold text-slate-900">{formatDateTime(activeComparison.result.provenance.retrieved_at)}</dd></div>
                    <div><dt className="text-xs text-slate-500">Requested period</dt><dd className="mt-1 font-semibold text-slate-900">{activeComparison.result.provenance.requested_period_start} to {activeComparison.result.provenance.requested_period_end}</dd></div>
                    <div><dt className="text-xs text-slate-500">Aligned period</dt><dd className="mt-1 font-semibold text-slate-900">{activeComparison.result.period_start} to {activeComparison.result.period_end}</dd></div>
                    <div><dt className="text-xs text-slate-500">Commission / slippage</dt><dd className="mt-1 font-semibold text-slate-900">{formatPercent(activeComparison.result.assumptions.commission_rate)} / {formatPercent(activeComparison.result.assumptions.slippage_rate)}</dd></div>
                    <div><dt className="text-xs text-slate-500">Engine version</dt><dd className="mt-1 font-semibold text-slate-900">{activeComparison.result.provenance.engine_version}</dd></div>
                    <div><dt className="text-xs text-slate-500">Actual portfolio return</dt><dd className="mt-1 font-semibold text-slate-900">{activeComparison.result.actual_portfolio?.return_method ?? "Not available"} · same aligned period</dd></div>
                  </dl>
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700"><p className="font-semibold text-slate-900">Turnover convention</p><p className="mt-1">{activeComparison.result.assumptions.turnover_convention}</p><p className="mt-2">Later actual ledger activity: {activeComparison.result.assumptions.later_actual_ledger_activity.replaceAll("_", " ")}.</p></div>
                </section>

                {activePolicy ? <PolicyDetail policy={activePolicy} currency={selectedPortfolio?.base_currency ?? "USD"} assetLabel={assetLabel} /> : null}
              </>
            ) : (
              <StatePanel title="No historical comparison selected" message="Run or reopen a comparison to review annual, quarterly, and threshold policy outcomes and their execution events." />
            )}
          </>
        )}
      </main>
    </DashboardShell>
  );
}
