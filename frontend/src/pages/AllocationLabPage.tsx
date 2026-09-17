import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import {
  Link,
  useParams,
  useSearchParams,
} from "react-router";

import { ApiError } from "../api/client";
import {
  AllocationComparisonChart,
  type AllocationComparisonRow,
} from "../components/charts/AllocationComparisonChart";
import { EfficientFrontierChart } from "../components/charts/EfficientFrontierChart";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  DASHBOARD_RANGES,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import {
  formatDateTime,
  humanizeCode,
} from "../features/dashboard/formatting";
import {
  latestSuccessfulOptimizationRun,
  optimizedWeightForAsset,
  type OptimizationControlContext,
} from "../features/optimization/optimizationTransforms";
import {
  useCreateOptimizationRun,
  useOptimizationRun,
  useOptimizationRuns,
} from "../hooks/useOptimizationData";
import {
  useDashboardSnapshot,
  usePortfolios,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type { DashboardHolding } from "../types/dashboard";
import type {
  OptimizationRun,
  OptimizationRunCreateRequest,
  OptimizationRunMethod,
  OptimizationRunStatus,
  OptimizationWeightBoundRequest,
} from "../types/optimization";

interface AssetControlState {
  selected: boolean;
  minimum: string;
  maximum: string;
}

const METHOD_OPTIONS: readonly {
  value: OptimizationRunMethod;
  label: string;
  description: string;
}[] = [
  {
    value: "EQUAL_WEIGHT",
    label: "Equal weight",
    description:
      "Server-calculated 1/N allocation subject to the submitted bounds.",
  },
  {
    value: "MINIMUM_VARIANCE",
    label: "Minimum variance",
    description:
      "Server-calculated long-only allocation minimizing historical annual variance.",
  },
  {
    value: "MAXIMUM_SHARPE",
    label: "Maximum Sharpe",
    description:
      "Server-calculated long-only allocation maximizing historical annual Sharpe.",
  },
  {
    value: "EFFICIENT_FRONTIER",
    label: "Efficient frontier",
    description:
      "Server-returned constrained minimum-variance portfolios across feasible target returns.",
  },
] as const;

function isDashboardRange(value: string | null): value is DashboardRange {
  return value !== null && DASHBOARD_RANGES.includes(value as DashboardRange);
}

function methodLabel(method: OptimizationRunMethod): string {
  return METHOD_OPTIONS.find((option) => option.value === method)?.label ?? method;
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(value);
}

function formatCount(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0,
  }).format(value);
}

function statusPresentation(status: OptimizationRunStatus): {
  label: string;
  className: string;
} {
  switch (status) {
    case "PENDING":
      return {
        label: "Pending",
        className: "border-slate-200 bg-slate-50 text-slate-700",
      };
    case "RUNNING":
      return {
        label: "Running",
        className: "border-blue-200 bg-blue-50 text-blue-800",
      };
    case "SUCCEEDED":
      return {
        label: "Succeeded",
        className: "border-emerald-200 bg-emerald-50 text-emerald-800",
      };
    case "FAILED":
      return {
        label: "Failed",
        className: "border-rose-200 bg-rose-50 text-rose-900",
      };
  }
}

function flattenErrorValue(value: unknown): string[] {
  if (typeof value === "string") {
    return [value];
  }

  if (Array.isArray(value)) {
    return value.flatMap(flattenErrorValue);
  }

  if (value !== null && typeof value === "object") {
    return Object.values(value).flatMap(flattenErrorValue);
  }

  return [];
}

function apiValidationErrors(error: ApiError | null): Record<string, string[]> {
  if (
    error === null ||
    error.status !== 400 ||
    error.payload === null ||
    typeof error.payload !== "object" ||
    !("errors" in error.payload)
  ) {
    return {};
  }

  const raw = error.payload.errors;
  if (raw === null || typeof raw !== "object") {
    return {};
  }

  return Object.fromEntries(
    Object.entries(raw).map(([field, value]) => [field, flattenErrorValue(value)]),
  );
}

function transportErrorTitle(error: Error): string {
  if (!(error instanceof ApiError)) {
    return "Allocation Lab could not load";
  }

  switch (error.status) {
    case 403:
      return "Portfolio access denied";
    case 404:
      return "Portfolio or optimization run not found";
    case 503:
      return "Optimization data provider unavailable";
    default:
      return "Allocation Lab could not load";
  }
}

function isEligibleHolding(holding: DashboardHolding): boolean {
  return (
    (holding.asset_type === "STOCK" || holding.asset_type === "ETF") &&
    holding.currency === "USD"
  );
}

function currentMethodDescription(method: OptimizationRunMethod): string {
  return METHOD_OPTIONS.find((option) => option.value === method)?.description ?? "";
}

function OptimizationMetric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </dt>
      <dd className="mt-2 text-xl font-semibold tabular-nums text-slate-950">
        {value}
      </dd>
    </div>
  );
}

function RunStatusPanel({ run }: { run: OptimizationRun }) {
  const presentation = statusPresentation(run.status);

  if (run.status === "PENDING" || run.status === "RUNNING") {
    return (
      <section
        className="rounded-3xl border border-blue-200 bg-blue-50 p-5 sm:p-6"
        aria-live="polite"
        aria-labelledby="optimization-progress-heading"
      >
        <div className="flex flex-wrap items-center gap-3">
          <h2
            id="optimization-progress-heading"
            className="text-lg font-semibold text-blue-950"
          >
            Optimization {presentation.label.toLowerCase()}
          </h2>
          <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${presentation.className}`}>
            {presentation.label}
          </span>
        </div>
        <p className="mt-2 text-sm leading-6 text-blue-900">
          Run {run.id} is persisted. The page will continue reading the server
          resource until it reaches a terminal state.
        </p>
      </section>
    );
  }

  if (run.status === "FAILED") {
    return (
      <section
        className="rounded-3xl border border-rose-200 bg-rose-50 p-5 sm:p-6"
        aria-labelledby="optimization-failed-heading"
        role="alert"
      >
        <div className="flex flex-wrap items-center gap-3">
          <h2
            id="optimization-failed-heading"
            className="text-lg font-semibold text-rose-950"
          >
            Optimization run failed
          </h2>
          <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${presentation.className}`}>
            {presentation.label}
          </span>
        </div>
        <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-rose-800">
          {humanizeCode(run.failure_code || "OPTIMIZATION_FAILED")}
        </p>
        <p className="mt-1 text-sm leading-6 text-rose-950">
          {run.failure_message || "The server did not provide a failure diagnostic."}
        </p>
        <p className="mt-3 text-xs text-rose-800">
          This failed run remains persisted as {run.id}. Adjust the controls and
          submit a new run rather than rewriting this resource.
        </p>
      </section>
    );
  }

  return null;
}

function SuccessfulRunResult({
  run,
  assetLabels,
}: {
  run: OptimizationRun;
  assetLabels: ReadonlyMap<string, string>;
}) {
  if (run.status !== "SUCCEEDED" || run.result === null) {
    return null;
  }

  const portfolio = run.result.portfolio;

  return (
    <section
      className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
      aria-labelledby="active-run-result-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
            Persisted server result
          </p>
          <h2
            id="active-run-result-heading"
            className="mt-1 text-lg font-semibold text-slate-950"
          >
            {methodLabel(run.method)}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Run {run.id}
          </p>
        </div>
        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
          Succeeded
        </span>
      </div>

      {portfolio ? (
        <>
          <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <OptimizationMetric
              label="Expected annual return"
              value={formatPercent(portfolio.expected_return)}
            />
            <OptimizationMetric
              label="Expected annual volatility"
              value={formatPercent(portfolio.expected_volatility)}
            />
            <OptimizationMetric
              label="Sharpe ratio"
              value={formatRatio(portfolio.sharpe_ratio)}
            />
            <OptimizationMetric
              label="Target return"
              value={formatPercent(portfolio.target_return)}
            />
          </dl>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[520px] border-collapse text-left text-sm">
              <caption className="sr-only">
                Server-provided optimized asset weights.
              </caption>
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-500">
                  <th className="py-2 pr-4 font-semibold">Asset</th>
                  <th className="py-2 font-semibold">Optimized weight</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.weights.map((weight) => (
                  <tr
                    key={weight.asset_id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <th className="py-2 pr-4 font-semibold text-slate-900">
                      {assetLabels.get(weight.asset_id) ?? weight.asset_id}
                    </th>
                    <td className="py-2 tabular-nums text-slate-700">
                      {formatPercent(weight.weight)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="mt-4 text-sm text-slate-600">
          This successful run contains frontier points rather than a single
          optimized portfolio.
        </p>
      )}

      {run.warnings.length > 0 ? (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="font-semibold text-amber-950">Server warnings</h3>
          <ul className="mt-2 space-y-2 text-sm text-amber-950">
            {run.warnings.map((warning) => (
              <li key={`${warning.code}-${warning.message}`}>
                <span className="font-semibold">{humanizeCode(warning.code)}:</span>{" "}
                {warning.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function RunProvenance({ run }: { run: OptimizationRun }) {
  return (
    <section
      className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
      aria-labelledby="optimization-provenance-heading"
    >
      <h2
        id="optimization-provenance-heading"
        className="text-lg font-semibold text-slate-950"
      >
        Assumptions and provenance
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Reproducibility metadata persisted with this optimization run.
      </p>

      <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <div>
          <dt className="text-xs text-slate-500">Requested period</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {run.provenance.period_start} to {run.provenance.period_end_exclusive}
            {" "}(end exclusive)
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Provider</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {run.provenance.provider || "Not available"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Price field</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {run.provenance.price_field || "Not available"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Annualization factor</dt>
          <dd className="mt-1 font-medium tabular-nums text-slate-900">
            {run.provenance.annualization_factor}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Risk-free rate</dt>
          <dd className="mt-1 font-medium tabular-nums text-slate-900">
            {formatPercent(run.provenance.risk_free_rate_annual)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Observations</dt>
          <dd className="mt-1 font-medium tabular-nums text-slate-900">
            {formatCount(run.parameters.observations)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Covariance rank</dt>
          <dd className="mt-1 font-medium tabular-nums text-slate-900">
            {formatCount(run.parameters.covariance_rank)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Benchmark asset</dt>
          <dd className="mt-1 break-all font-medium text-slate-900">
            {run.provenance.benchmark_asset_id ?? "Not configured"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Engine version</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {run.provenance.engine_version || "Not available"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Method version</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {run.provenance.method_version || "Not available"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Data retrieved</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {formatDateTime(run.provenance.data_retrieved_at)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Completed</dt>
          <dd className="mt-1 font-medium text-slate-900">
            {formatDateTime(run.completed_at)}
          </dd>
        </div>
        <div className="sm:col-span-2 xl:col-span-4">
          <dt className="text-xs text-slate-500">Source-data fingerprint</dt>
          <dd className="mt-1 break-all font-mono text-xs text-slate-700">
            {run.provenance.data_fingerprint || "Not available"}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function AllocationLabSkeleton() {
  return (
    <div aria-label="Loading Allocation Lab">
      <Skeleton className="h-64 w-full rounded-3xl" />
      <Skeleton className="mt-5 h-72 w-full rounded-3xl" />
    </div>
  );
}

export function AllocationLabPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const [searchParams] = useSearchParams();
  const rangeParam = searchParams.get("range");
  const range: DashboardRange = isDashboardRange(rangeParam) ? rangeParam : "1M";

  const portfoliosQuery = usePortfolios();
  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );

  const dashboardDates = useMemo(() => {
    if (!selectedPortfolio) {
      return null;
    }
    return resolveDashboardDateRange(range, selectedPortfolio.created_at);
  }, [range, selectedPortfolio]);

  const dashboardRequest =
    portfolioId && dashboardDates
      ? {
          portfolioId,
          start: dashboardDates.start,
          end: dashboardDates.end,
        }
      : null;

  const snapshotQuery = useDashboardSnapshot(dashboardRequest);
  const scopedPortfolioId = selectedPortfolio?.id ?? null;
  const runsQuery = useOptimizationRuns(scopedPortfolioId);
  const createRun = useCreateOptimizationRun(scopedPortfolioId);

  const [startOverride, setStartOverride] = useState<string | null>(null);
  const [endOverride, setEndOverride] = useState<string | null>(null);
  const [method, setMethod] = useState<OptimizationRunMethod>("MINIMUM_VARIANCE");
  const [frontierPoints, setFrontierPoints] = useState("25");
  const [assetControls, setAssetControls] = useState<Record<string, AssetControlState>>({});
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const start = startOverride ?? dashboardDates?.start ?? "";
  const end = endOverride ?? dashboardDates?.end ?? "";

  const eligibleHoldings = useMemo(
    () =>
      snapshotQuery.data?.holdings?.holdings.filter(isEligibleHolding) ?? [],
    [snapshotQuery.data?.holdings?.holdings],
  );

  useEffect(() => {
    if (eligibleHoldings.length === 0) {
      return;
    }

    setAssetControls((current) => {
      const next = { ...current };
      let changed = false;

      for (const holding of eligibleHoldings) {
        if (!(holding.asset_id in next)) {
          next[holding.asset_id] = {
            selected: true,
            minimum: "0",
            maximum: "1",
          };
          changed = true;
        }
      }

      return changed ? next : current;
    });
  }, [eligibleHoldings]);

  const selectedAssetIds = useMemo(
    () =>
      eligibleHoldings
        .filter((holding) => assetControls[holding.asset_id]?.selected ?? false)
        .map((holding) => holding.asset_id),
    [assetControls, eligibleHoldings],
  );

  const submittedBounds = useMemo<OptimizationWeightBoundRequest[]>(
    () =>
      selectedAssetIds.flatMap((assetId) => {
        const control = assetControls[assetId];
        if (!control) {
          return [];
        }
        return [
          {
            asset_id: assetId,
            minimum:
              control.minimum.trim() === "" ? Number.NaN : Number(control.minimum),
            maximum:
              control.maximum.trim() === "" ? Number.NaN : Number(control.maximum),
          },
        ];
      }),
    [assetControls, selectedAssetIds],
  );

  const controlContext: OptimizationControlContext = useMemo(
    () => ({
      start,
      end,
      assetIds: selectedAssetIds,
      bounds: submittedBounds,
    }),
    [end, selectedAssetIds, start, submittedBounds],
  );

  const activeRunQuery = useOptimizationRun(activeRunId);
  const activeRun = activeRunQuery.data ?? null;

  const availableRuns = useMemo(() => {
    const runs = runsQuery.data ?? [];
    if (activeRun === null || runs.some((run) => run.id === activeRun.id)) {
      return runs;
    }
    return [activeRun, ...runs];
  }, [activeRun, runsQuery.data]);

  const equalWeightRun = latestSuccessfulOptimizationRun(
    availableRuns,
    "EQUAL_WEIGHT",
    controlContext,
  );
  const minimumVarianceRun = latestSuccessfulOptimizationRun(
    availableRuns,
    "MINIMUM_VARIANCE",
    controlContext,
  );
  const maximumSharpeRun = latestSuccessfulOptimizationRun(
    availableRuns,
    "MAXIMUM_SHARPE",
    controlContext,
  );
  const frontierRun = latestSuccessfulOptimizationRun(
    availableRuns,
    "EFFICIENT_FRONTIER",
    controlContext,
  );

  const frontierPointsForContext = frontierRun?.result?.frontier ?? [];

  const holdingByAsset = useMemo(
    () => new Map(eligibleHoldings.map((holding) => [holding.asset_id, holding] as const)),
    [eligibleHoldings],
  );

  const assetLabels = useMemo(
    () =>
      new Map(
        eligibleHoldings.map(
          (holding) => [holding.asset_id, `${holding.symbol} · ${holding.name}`] as const,
        ),
      ),
    [eligibleHoldings],
  );

  const comparisonRows = useMemo<AllocationComparisonRow[]>(
    () =>
      selectedAssetIds.map((assetId) => {
        const holding = holdingByAsset.get(assetId);
        return {
          assetId,
          label: holding ? holding.symbol : assetId,
          currentWeight: holding?.weight ?? null,
          equalWeight: optimizedWeightForAsset(equalWeightRun, assetId),
          minimumVarianceWeight: optimizedWeightForAsset(minimumVarianceRun, assetId),
          maximumSharpeWeight: optimizedWeightForAsset(maximumSharpeRun, assetId),
        };
      }),
    [
      equalWeightRun,
      holdingByAsset,
      maximumSharpeRun,
      minimumVarianceRun,
      selectedAssetIds,
    ],
  );

  const createApiError = createRun.error instanceof ApiError ? createRun.error : null;
  const validationErrors = apiValidationErrors(createApiError);

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          {portfolioId ? (
            <Link
              to={`/portfolios/${encodeURIComponent(portfolioId)}/dashboard?range=${encodeURIComponent(range)}`}
              className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Portfolio dashboard
            </Link>
          ) : null}
          <span aria-hidden="true">/</span>
          <span>Allocation Lab</span>
        </div>
        <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          Allocation Lab
        </h1>
        {selectedPortfolio ? (
          <p className="mt-1 truncate text-xs font-medium text-slate-500">
            {selectedPortfolio.name}
          </p>
        ) : null}
      </div>
      <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-800">
        Hypothetical optimization
      </span>
    </div>
  );

  function updateAssetControl(
    assetId: string,
    patch: Partial<AssetControlState>,
  ) {
    setAssetControls((current) => ({
      ...current,
      [assetId]: {
        selected: current[assetId]?.selected ?? true,
        minimum: current[assetId]?.minimum ?? "0",
        maximum: current[assetId]?.maximum ?? "1",
        ...patch,
      },
    }));
  }

  async function submitOptimization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!portfolioId) {
      setFormError("Portfolio context is unavailable.");
      return;
    }
    if (!start || !end || start >= end) {
      setFormError("Choose a start date earlier than the exclusive end date.");
      return;
    }
    if (selectedAssetIds.length === 0) {
      setFormError("Select at least one eligible held asset.");
      return;
    }

    for (const bound of submittedBounds) {
      if (
        !Number.isFinite(bound.minimum) ||
        !Number.isFinite(bound.maximum) ||
        bound.minimum < 0 ||
        bound.maximum > 1 ||
        bound.minimum > bound.maximum
      ) {
        setFormError(
          "Each selected asset requires finite bounds between 0 and 1 with minimum no greater than maximum.",
        );
        return;
      }
    }

    const request: OptimizationRunCreateRequest = {
      portfolio_id: portfolioId,
      method,
      start,
      end,
      asset_ids: selectedAssetIds,
      bounds: submittedBounds,
    };

    if (method === "EFFICIENT_FRONTIER") {
      const parsedFrontierPoints = Number(frontierPoints);
      if (
        !Number.isInteger(parsedFrontierPoints) ||
        parsedFrontierPoints < 2 ||
        parsedFrontierPoints > 100
      ) {
        setFormError("Efficient-frontier points must be an integer from 2 through 100.");
        return;
      }
      request.frontier_points = parsedFrontierPoints;
    }

    setFormError(null);

    try {
      const run = await createRun.mutateAsync(request);
      setActiveRunId(run.id);
    } catch {
      // Mutation state renders the authoritative transport/validation failure.
    }
  }

  if (portfoliosQuery.isPending && selectedPortfolio === undefined) {
    return (
      <DashboardShell header={header}>
        <AllocationLabSkeleton />
      </DashboardShell>
    );
  }

  if (!portfoliosQuery.isPending && portfoliosQuery.data && !selectedPortfolio) {
    return (
      <DashboardShell header={header}>
        <StatePanel
          title="Portfolio not found"
          message="This portfolio is not available in the authenticated account scope."
          tone="error"
          action={
            <Link
              to="/"
              className="inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Choose a portfolio
            </Link>
          }
        />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell header={header}>
      <section className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-600">
            Server-authoritative historical optimization. Results are hypothetical
            analysis, not trade instructions, and no portfolio ledger or holdings are
            mutated by this page.
          </p>
          {portfolioId ? (
            <div className="mt-2 flex flex-wrap gap-4 text-sm font-semibold">
              <Link
                to={`/portfolios/${encodeURIComponent(portfolioId)}/dashboard?range=${encodeURIComponent(range)}`}
                className="text-slate-700 outline-none underline decoration-slate-200 underline-offset-4 hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                ← Back to dashboard
              </Link>
              <Link
                to={`/portfolios/${encodeURIComponent(portfolioId)}/analysis?range=${encodeURIComponent(range)}`}
                className="text-blue-700 outline-none underline decoration-blue-200 underline-offset-4 hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                Portfolio analysis
              </Link>
            </div>
          ) : null}
        </div>
        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
          Range context {range}
        </span>
      </section>

      {snapshotQuery.isPending && snapshotQuery.data === undefined ? (
        <AllocationLabSkeleton />
      ) : snapshotQuery.error instanceof Error && snapshotQuery.data === undefined ? (
        <StatePanel
          title={transportErrorTitle(snapshotQuery.error)}
          message={snapshotQuery.error.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => void snapshotQuery.refetch()}
              className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Retry portfolio data
            </button>
          }
        />
      ) : eligibleHoldings.length === 0 ? (
        <StatePanel
          title="No eligible holdings"
          message="The selected portfolio has no current supported USD stock or ETF holdings available for optimization. Add eligible holdings before creating an optimization run."
        />
      ) : (
        <>
          <section
            className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            aria-labelledby="optimization-controls-heading"
          >
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-700">
                Optimization controls
              </p>
              <h2
                id="optimization-controls-heading"
                className="mt-1 text-lg font-semibold text-slate-950"
              >
                Create a persisted optimization run
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-600">
                Ticker labels are for display only. Requests submit canonical asset
                IDs and the backend remains authoritative for feasibility, market
                data, estimation, solving, and post-solver validation.
              </p>
            </div>

            <form className="mt-5 space-y-5" onSubmit={submitOptimization}>
              <div className="grid gap-4 md:grid-cols-4">
                <label className="text-xs font-semibold text-slate-700">
                  Start
                  <input
                    type="date"
                    value={start}
                    onChange={(event) => setStartOverride(event.target.value)}
                    className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  />
                </label>

                <label className="text-xs font-semibold text-slate-700">
                  End (exclusive)
                  <input
                    type="date"
                    value={end}
                    onChange={(event) => setEndOverride(event.target.value)}
                    className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  />
                </label>

                <div className="md:col-span-2">
                  <label
                    htmlFor="optimization-method"
                    className="text-xs font-semibold text-slate-700"
                  >
                    Optimization method
                  </label>
                  <select
                    id="optimization-method"
                    aria-describedby="optimization-method-description"
                    value={method}
                    onChange={(event) =>
                      setMethod(event.target.value as OptimizationRunMethod)
                    }
                    className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    {METHOD_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <span
                    id="optimization-method-description"
                    className="mt-1 block text-xs font-normal leading-5 text-slate-500"
                  >
                    {currentMethodDescription(method)}
                  </span>
                </div>
              </div>

              {method === "EFFICIENT_FRONTIER" ? (
                <div className="max-w-xs">
                  <label
                    htmlFor="frontier-points"
                    className="block text-xs font-semibold text-slate-700"
                  >
                    Frontier points
                  </label>
                  <input
                    id="frontier-points"
                    type="number"
                    min={2}
                    max={100}
                    step={1}
                    value={frontierPoints}
                    aria-describedby="frontier-points-description"
                    onChange={(event) => setFrontierPoints(event.target.value)}
                    className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-normal tabular-nums text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  />
                  <span
                    id="frontier-points-description"
                    className="mt-1 block text-xs font-normal text-slate-500"
                  >
                    Only the exact server-returned points will be displayed.
                  </span>
                </div>
              ) : null}

              <fieldset>
                <legend className="text-sm font-semibold text-slate-950">
                  Eligible held assets and bounds
                </legend>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Bounds are decimal portfolio weights from 0 through 1. They are
                  submitted unchanged; the backend rejects infeasible combinations.
                </p>

                <div className="mt-3 overflow-x-auto rounded-2xl border border-slate-200">
                  <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 text-xs text-slate-500">
                        <th className="px-4 py-3 font-semibold">Include</th>
                        <th className="px-4 py-3 font-semibold">Asset</th>
                        <th className="px-4 py-3 font-semibold">Current weight</th>
                        <th className="px-4 py-3 font-semibold">Minimum</th>
                        <th className="px-4 py-3 font-semibold">Maximum</th>
                      </tr>
                    </thead>
                    <tbody>
                      {eligibleHoldings.map((holding) => {
                        const control = assetControls[holding.asset_id] ?? {
                          selected: false,
                          minimum: "0",
                          maximum: "1",
                        };
                        const symbolId = `optimization-asset-${holding.asset_id}`;
                        return (
                          <tr
                            key={holding.asset_id}
                            className="border-b border-slate-100 last:border-0"
                          >
                            <td className="px-4 py-3">
                              <input
                                id={symbolId}
                                type="checkbox"
                                aria-label={`${holding.symbol} ${holding.name}`}
                                checked={control.selected}
                                onChange={(event) =>
                                  updateAssetControl(holding.asset_id, {
                                    selected: event.target.checked,
                                  })
                                }
                                className="h-4 w-4 rounded border-slate-300 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                              />
                            </td>
                            <th className="px-4 py-3 font-semibold text-slate-900">
                              <span>
                                {holding.symbol}
                                <span className="ml-2 font-normal text-slate-500">
                                  {holding.name}
                                </span>
                              </span>
                              <span className="mt-0.5 block break-all text-[11px] font-normal text-slate-400">
                                {holding.asset_id}
                              </span>
                            </th>
                            <td className="px-4 py-3 tabular-nums text-slate-700">
                              {formatPercent(holding.weight)}
                            </td>
                            <td className="px-4 py-3">
                              <label className="sr-only" htmlFor={`min-${holding.asset_id}`}>
                                {holding.symbol} minimum weight
                              </label>
                              <input
                                id={`min-${holding.asset_id}`}
                                type="number"
                                min={0}
                                max={1}
                                step="0.01"
                                disabled={!control.selected}
                                value={control.minimum}
                                onChange={(event) =>
                                  updateAssetControl(holding.asset_id, {
                                    minimum: event.target.value,
                                  })
                                }
                                className="w-28 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400"
                              />
                            </td>
                            <td className="px-4 py-3">
                              <label className="sr-only" htmlFor={`max-${holding.asset_id}`}>
                                {holding.symbol} maximum weight
                              </label>
                              <input
                                id={`max-${holding.asset_id}`}
                                type="number"
                                min={0}
                                max={1}
                                step="0.01"
                                disabled={!control.selected}
                                value={control.maximum}
                                onChange={(event) =>
                                  updateAssetControl(holding.asset_id, {
                                    maximum: event.target.value,
                                  })
                                }
                                className="w-28 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-400"
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </fieldset>

              {formError ? (
                <p role="alert" className="text-sm font-medium text-rose-700">
                  {formError}
                </p>
              ) : null}

              {Object.keys(validationErrors).length > 0 ? (
                <div
                  className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-950"
                  role="alert"
                >
                  <p className="font-semibold">Server validation errors</p>
                  <ul className="mt-2 space-y-1">
                    {Object.entries(validationErrors).flatMap(([field, messages]) =>
                      messages.map((message) => (
                        <li key={`${field}-${message}`}>
                          <span className="font-semibold">
                            {humanizeCode(field) ?? field}:
                          </span>{" "}
                          {message}
                        </li>
                      )),
                    )}
                  </ul>
                </div>
              ) : null}

              {createRun.error instanceof Error && createApiError?.status !== 400 ? (
                <StatePanel
                  title={transportErrorTitle(createRun.error)}
                  message={createRun.error.message}
                  tone="error"
                />
              ) : null}

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  disabled={createRun.isPending}
                  className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {createRun.isPending ? "Creating run…" : "Run optimization"}
                </button>
                <span className="text-xs text-slate-500">
                  Risk-free-rate behavior remains backend-authoritative; this form
                  does not submit a frontend assumption.
                </span>
              </div>
            </form>
          </section>

          <div className="mt-5 space-y-5">
            {runsQuery.error instanceof Error ? (
              <div
                className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
                role="status"
              >
                Persisted run history could not refresh. New optimization runs can
                still be created; comparison history may be incomplete.
              </div>
            ) : null}

            {runsQuery.data && runsQuery.data.length > 0 ? (
              <section
                className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                aria-labelledby="recent-optimization-runs-heading"
              >
                <h2
                  id="recent-optimization-runs-heading"
                  className="text-lg font-semibold text-slate-950"
                >
                  Recent persisted runs
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Inspect a prior owner-scoped run and its stored assumptions,
                  diagnostics, and provenance.
                </p>
                <ul className="mt-4 space-y-2">
                  {runsQuery.data.slice(0, 5).map((run) => {
                    const presentation = statusPresentation(run.status);
                    return (
                      <li
                        key={run.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 px-4 py-3"
                      >
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-slate-950">
                              {methodLabel(run.method)}
                            </span>
                            <span
                              className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${presentation.className}`}
                            >
                              {presentation.label}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            {run.provenance.period_start} to{" "}
                            {run.provenance.period_end_exclusive} · {run.id}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveRunId(run.id)}
                          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                        >
                          Inspect run
                          <span className="sr-only"> {run.id}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ) : null}

            {activeRunQuery.error instanceof Error && activeRun === null ? (
              <StatePanel
                title={transportErrorTitle(activeRunQuery.error)}
                message={activeRunQuery.error.message}
                tone="error"
                action={
                  <button
                    type="button"
                    onClick={() => void activeRunQuery.refetch()}
                    className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                  >
                    Retry run lookup
                  </button>
                }
              />
            ) : null}

            {activeRun ? <RunStatusPanel run={activeRun} /> : null}
            {activeRun ? (
              <SuccessfulRunResult run={activeRun} assetLabels={assetLabels} />
            ) : null}

            <section
              className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              aria-labelledby="allocation-comparison-heading"
            >
              <h2
                id="allocation-comparison-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Allocation comparison
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Current weights come from the authoritative dashboard holdings
                snapshot and are not renormalized when cash or excluded holdings
                exist. Optimized columns appear only for matching successful
                persisted runs using this period, asset universe, and bounds.
              </p>

              <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold">
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-700">
                  Current observed
                </span>
                <span
                  className={`rounded-full border px-2.5 py-1 ${
                    equalWeightRun
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-slate-200 bg-slate-50 text-slate-500"
                  }`}
                >
                  Equal weight {equalWeightRun ? "available" : "not run"}
                </span>
                <span
                  className={`rounded-full border px-2.5 py-1 ${
                    minimumVarianceRun
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-slate-200 bg-slate-50 text-slate-500"
                  }`}
                >
                  Minimum variance {minimumVarianceRun ? "available" : "not run"}
                </span>
                <span
                  className={`rounded-full border px-2.5 py-1 ${
                    maximumSharpeRun
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : "border-slate-200 bg-slate-50 text-slate-500"
                  }`}
                >
                  Maximum Sharpe {maximumSharpeRun ? "available" : "not run"}
                </span>
              </div>

              <div className="mt-5">
                <AllocationComparisonChart rows={comparisonRows} />
              </div>
            </section>

            {frontierPointsForContext.length > 0 && frontierRun ? (
              <section
                className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                aria-labelledby="efficient-frontier-heading"
              >
                <h2
                  id="efficient-frontier-heading"
                  className="text-lg font-semibold text-slate-950"
                >
                  Efficient frontier
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  Expected annual volatility is plotted against expected annual
                  return using exactly the points returned by persisted run
                  {" "}{frontierRun.id}. The browser does not interpolate the frontier.
                </p>
                <div className="mt-4">
                  <EfficientFrontierChart
                    points={frontierPointsForContext}
                    assetLabels={assetLabels}
                  />
                </div>
              </section>
            ) : (
              <section className="rounded-3xl border border-slate-200 bg-slate-50 p-5 sm:p-6">
                <h2 className="text-lg font-semibold text-slate-900">
                  Efficient frontier not generated yet
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  Select Efficient frontier and create a matching persisted run to
                  populate this section.
                </p>
              </section>
            )}

            {activeRun ? <RunProvenance run={activeRun} /> : null}
          </div>
        </>
      )}
    </DashboardShell>
  );
}
