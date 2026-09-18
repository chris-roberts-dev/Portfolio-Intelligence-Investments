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
import { DomainPageHeader } from "../components/ui/DomainPageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  DASHBOARD_RANGES,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
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
  useAssetCatalog,
  useDashboardSnapshot,
  usePortfolios,
  useResolveAssets,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type {
  OptimizationBaselineWeightRequest,
  OptimizationRun,
  OptimizationRunCreateRequest,
  OptimizationRunMethod,
  OptimizationRunStatus,
  OptimizationWeightBoundRequest,
} from "../types/optimization";
import type { AssetCatalogItem } from "../types/portfolioManagement";

type SourceMode = "AD_HOC" | "PORTFOLIO";

interface AssetControlState {
  asset: AssetCatalogItem;
  minimum: string;
  maximum: string;
  baseline: string;
}

const METHOD_OPTIONS: readonly {
  value: OptimizationRunMethod;
  label: string;
}[] = [
  { value: "EQUAL_WEIGHT", label: "Equal weight" },
  { value: "MINIMUM_VARIANCE", label: "Minimum variance" },
  { value: "MAXIMUM_SHARPE", label: "Maximum Sharpe" },
  { value: "EFFICIENT_FRONTIER", label: "Efficient frontier" },
] as const;

function isDashboardRange(value: string | null): value is DashboardRange {
  return value !== null && DASHBOARD_RANGES.includes(value as DashboardRange);
}

function formatLocalDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultDates(): { start: string; end: string } {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
  return { start: formatLocalDate(start), end: formatLocalDate(end) };
}

function parseSymbols(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(/[\s,]+/)
    .map((symbol) => symbol.trim().toUpperCase())
    .filter((symbol) => {
      if (!symbol || seen.has(symbol)) {
        return false;
      }
      seen.add(symbol);
      return true;
    });
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

function statusLabel(status: OptimizationRunStatus): string {
  switch (status) {
    case "PENDING":
      return "Pending";
    case "RUNNING":
      return "Running";
    case "SUCCEEDED":
      return "Succeeded";
    case "FAILED":
      return "Failed";
  }
}

function errorTitle(error: Error): string {
  if (!(error instanceof ApiError)) {
    return "Optimization request failed";
  }
  if (error.status === 400) {
    return "Optimization configuration is invalid";
  }
  if (error.status === 403) {
    return "Optimization access denied";
  }
  if (error.status === 404) {
    return "Optimization source was not found";
  }
  if (error.status === 503) {
    return "Optimization data provider unavailable";
  }
  return "Optimization request failed";
}

function runSourceLabel(run: OptimizationRun): string {
  return run.source_type === "AD_HOC"
    ? "Ad hoc"
    : `Portfolio-derived${run.portfolio_name ? ` · ${run.portfolio_name}` : ""}`;
}

function LabSkeleton() {
  return (
    <div aria-label="Loading Allocation Lab">
      <Skeleton className="h-40 w-full rounded-2xl" />
      <Skeleton className="mt-5 h-96 w-full rounded-2xl" />
    </div>
  );
}

export function AllocationLabPage() {
  const { portfolioId: legacyPortfolioId } =
    useParams<{ portfolioId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryPortfolioId = searchParams.get("portfolio");
  const rangeParam = searchParams.get("range");
  const requestedPortfolioId = legacyPortfolioId ?? queryPortfolioId;
  const initialMode: SourceMode = requestedPortfolioId ? "PORTFOLIO" : "AD_HOC";
  const defaults = useMemo(defaultDates, []);

  const [sourceMode, setSourceMode] = useState<SourceMode>(initialMode);
  const [portfolioId, setPortfolioId] = useState(requestedPortfolioId ?? "");
  const [start, setStart] = useState(defaults.start);
  const [end, setEnd] = useState(defaults.end);
  const [method, setMethod] =
    useState<OptimizationRunMethod>("MINIMUM_VARIANCE");
  const [riskFreeRate, setRiskFreeRate] = useState("0");
  const [frontierPoints, setFrontierPoints] = useState("25");
  const [symbolInput, setSymbolInput] = useState("");
  const [assets, setAssets] = useState<Record<string, AssetControlState>>({});
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [assetMessage, setAssetMessage] = useState<string | null>(null);

  const portfoliosQuery = usePortfolios();
  const assetCatalogQuery = useAssetCatalog();
  const resolveAssetsMutation = useResolveAssets();
  const runsQuery = useOptimizationRuns();
  const createRun = useCreateOptimizationRun();
  const activeRunQuery = useOptimizationRun(activeRunId);

  const dashboardRequest =
    sourceMode === "PORTFOLIO" && portfolioId && start < end
      ? { portfolioId, start, end }
      : null;
  const snapshotQuery = useDashboardSnapshot(dashboardRequest);
  const selectedPortfolio =
    portfoliosQuery.data?.find((portfolio) => portfolio.id === portfolioId) ?? null;

  const selectedAssets = useMemo(
    () => Object.values(assets),
    [assets],
  );
  const selectedAssetIds = useMemo(
    () => selectedAssets.map((item) => item.asset.id),
    [selectedAssets],
  );
  const assetLabels = useMemo(
    () =>
      new Map(
        selectedAssets.map(
          (item) =>
            [
              item.asset.id,
              `${item.asset.symbol} — ${item.asset.name}`,
            ] as const,
        ),
      ),
    [selectedAssets],
  );

  const parsedRiskFreeRate = Number(riskFreeRate);
  const submittedBounds = useMemo<OptimizationWeightBoundRequest[]>(
    () =>
      selectedAssets
        .filter((item) => item.minimum !== "" || item.maximum !== "")
        .map((item) => ({
          asset_id: item.asset.id,
          minimum: Number(item.minimum || "0"),
          maximum: Number(item.maximum || "1"),
        })),
    [selectedAssets],
  );

  const comparisonContext = useMemo<OptimizationControlContext | null>(() => {
    if (!start || !end || !Number.isFinite(parsedRiskFreeRate)) {
      return null;
    }
    return {
      sourceType: sourceMode,
      portfolioId: sourceMode === "PORTFOLIO" ? portfolioId || null : null,
      start,
      end,
      assetIds: selectedAssetIds,
      bounds: submittedBounds,
      riskFreeRateAnnual: parsedRiskFreeRate,
    };
  }, [
    end,
    parsedRiskFreeRate,
    portfolioId,
    selectedAssetIds,
    sourceMode,
    start,
    submittedBounds,
  ]);

  const availableRuns = runsQuery.data ?? [];
  const equalRun =
    comparisonContext === null
      ? null
      : latestSuccessfulOptimizationRun(
          availableRuns,
          "EQUAL_WEIGHT",
          comparisonContext,
        );
  const minimumVarianceRun =
    comparisonContext === null
      ? null
      : latestSuccessfulOptimizationRun(
          availableRuns,
          "MINIMUM_VARIANCE",
          comparisonContext,
        );
  const maximumSharpeRun =
    comparisonContext === null
      ? null
      : latestSuccessfulOptimizationRun(
          availableRuns,
          "MAXIMUM_SHARPE",
          comparisonContext,
        );
  const frontierRun =
    comparisonContext === null
      ? null
      : latestSuccessfulOptimizationRun(
          availableRuns,
          "EFFICIENT_FRONTIER",
          comparisonContext,
        );

  const currentHoldingWeightByAsset = useMemo(() => {
    const map = new Map<string, number | null>();
    for (const holding of snapshotQuery.data?.holdings?.holdings ?? []) {
      map.set(holding.asset_id, holding.weight);
    }
    return map;
  }, [snapshotQuery.data?.holdings?.holdings]);

  const comparisonRows = useMemo<AllocationComparisonRow[]>(
    () =>
      selectedAssets.map((item) => {
        const baseline =
          sourceMode === "AD_HOC" && item.baseline !== ""
            ? Number(item.baseline)
            : sourceMode === "PORTFOLIO"
              ? currentHoldingWeightByAsset.get(item.asset.id) ?? null
              : null;

        return {
          assetId: item.asset.id,
          label: item.asset.symbol,
          currentWeight: Number.isFinite(baseline) ? baseline : null,
          equalWeight: optimizedWeightForAsset(equalRun, item.asset.id),
          minimumVarianceWeight: optimizedWeightForAsset(
            minimumVarianceRun,
            item.asset.id,
          ),
          maximumSharpeWeight: optimizedWeightForAsset(
            maximumSharpeRun,
            item.asset.id,
          ),
        };
      }),
    [
      currentHoldingWeightByAsset,
      equalRun,
      maximumSharpeRun,
      minimumVarianceRun,
      selectedAssets,
      sourceMode,
    ],
  );

  const activeRun =
    activeRunQuery.data ??
    availableRuns.find((run) => run.id === activeRunId) ??
    null;

  useEffect(() => {
    if (legacyPortfolioId) {
      setSourceMode("PORTFOLIO");
      setPortfolioId(legacyPortfolioId);
    }
  }, [legacyPortfolioId]);

  useEffect(() => {
    if (
      sourceMode !== "PORTFOLIO" ||
      selectedPortfolio === null ||
      !isDashboardRange(rangeParam)
    ) {
      return;
    }

    const dates = resolveDashboardDateRange(
      rangeParam,
      selectedPortfolio.created_at,
      selectedPortfolio.ledger_inception_at,
    );
    setStart(dates.start);
    setEnd(dates.end);
  }, [rangeParam, selectedPortfolio, sourceMode]);

  function updateSourceMode(next: SourceMode) {
    setSourceMode(next);
    setActiveRunId(null);
    setAssets({});
    setFormError(null);
    setAssetMessage(null);

    const nextParams = new URLSearchParams(searchParams);
    if (next === "AD_HOC") {
      nextParams.delete("portfolio");
      setPortfolioId("");
    } else if (portfolioId) {
      nextParams.set("portfolio", portfolioId);
    }
    if (!legacyPortfolioId) {
      setSearchParams(nextParams, { replace: true });
    }
  }

  function updatePortfolio(nextPortfolioId: string) {
    setPortfolioId(nextPortfolioId);
    setAssets({});
    const nextParams = new URLSearchParams(searchParams);
    if (nextPortfolioId) {
      nextParams.set("portfolio", nextPortfolioId);
    } else {
      nextParams.delete("portfolio");
    }
    if (!legacyPortfolioId) {
      setSearchParams(nextParams, { replace: true });
    }
  }

  async function addSymbols(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const symbols = parseSymbols(symbolInput);
    if (symbols.length === 0) {
      setAssetMessage("Enter at least one ticker symbol.");
      return;
    }

    try {
      const result = await resolveAssetsMutation.mutateAsync({ symbols });
      setAssets((currentAssets) => {
        const next = { ...currentAssets };
        for (const outcome of result.outcomes) {
          if (outcome.status === "RESOLVED" && outcome.asset !== null) {
            next[outcome.asset.id] ??= {
              asset: outcome.asset,
              minimum: "0",
              maximum: "1",
              baseline: "",
            };
          }
        }
        return next;
      });

      const unresolved = result.outcomes.filter(
        (outcome) => outcome.status !== "RESOLVED",
      );
      setAssetMessage(
        unresolved.length === 0
          ? `Added ${result.outcomes.length} canonical asset${
              result.outcomes.length === 1 ? "" : "s"
            }.`
          : unresolved
              .map(
                (outcome) =>
                  `${outcome.symbol}: ${outcome.warning ?? outcome.status}`,
              )
              .join(" · "),
      );
      setSymbolInput("");
    } catch (error) {
      setAssetMessage(
        error instanceof Error ? error.message : "Asset resolution failed.",
      );
    }
  }

  function importPortfolioHoldings() {
    const holdings = snapshotQuery.data?.holdings?.holdings ?? [];
    const catalogById = new Map(
      (assetCatalogQuery.data ?? []).map((asset) => [asset.id, asset] as const),
    );

    const next: Record<string, AssetControlState> = {};
    for (const holding of holdings) {
      if (
        holding.asset_type !== "STOCK" &&
        holding.asset_type !== "ETF"
      ) {
        continue;
      }
      const catalogAsset = catalogById.get(holding.asset_id);
      const asset: AssetCatalogItem =
        catalogAsset ?? {
          id: holding.asset_id,
          symbol: holding.symbol,
          name: holding.name,
          asset_type: holding.asset_type,
          exchange: "",
          currency: holding.currency,
        };
      next[asset.id] = {
        asset,
        minimum: "0",
        maximum: "1",
        baseline: "",
      };
    }
    setAssets(next);
    setAssetMessage(
      Object.keys(next).length > 0
        ? `Imported ${Object.keys(next).length} current eligible holding${
            Object.keys(next).length === 1 ? "" : "s"
          } without changing the portfolio.`
        : "This portfolio has no eligible current stock/ETF holdings to import.",
    );
  }

  function removeAsset(assetId: string) {
    setAssets((currentAssets) => {
      const next = { ...currentAssets };
      delete next[assetId];
      return next;
    });
  }

  function updateAssetControl(
    assetId: string,
    field: "minimum" | "maximum" | "baseline",
    value: string,
  ) {
    setAssets((currentAssets) => ({
      ...currentAssets,
      [assetId]: {
        ...currentAssets[assetId]!,
        [field]: value,
      },
    }));
  }

  function baselineRequest():
    | OptimizationBaselineWeightRequest[]
    | undefined {
    if (sourceMode !== "AD_HOC") {
      return undefined;
    }
    const values = selectedAssets.map((item) => item.baseline);
    const anySupplied = values.some((value) => value !== "");
    if (!anySupplied) {
      return undefined;
    }
    if (values.some((value) => value === "")) {
      throw new Error(
        "If a custom baseline is supplied, enter a baseline weight for every selected asset.",
      );
    }
    const baseline = selectedAssets.map((item) => ({
      asset_id: item.asset.id,
      weight: Number(item.baseline),
    }));
    if (baseline.some((item) => !Number.isFinite(item.weight) || item.weight < 0 || item.weight > 1)) {
      throw new Error("Baseline weights must be finite values from 0 through 1.");
    }
    const total = baseline.reduce((sum, item) => sum + item.weight, 0);
    if (Math.abs(total - 1) > 1e-8) {
      throw new Error("Complete custom baseline weights must sum to 100%.");
    }
    return baseline;
  }

  async function submitOptimization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!start || !end || start >= end) {
      setFormError("Choose a start date earlier than the exclusive end date.");
      return;
    }
    if (selectedAssetIds.length === 0) {
      setFormError("Add at least one canonical asset to the optimization universe.");
      return;
    }
    if (!Number.isFinite(parsedRiskFreeRate)) {
      setFormError("Annual risk-free rate must be a finite decimal value.");
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
          "Every asset bound must satisfy 0 ≤ minimum ≤ maximum ≤ 1.",
        );
        return;
      }
    }

    let baseline: OptimizationBaselineWeightRequest[] | undefined;
    try {
      baseline = baselineRequest();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Invalid baseline.");
      return;
    }

    const request: OptimizationRunCreateRequest = {
      source_type: sourceMode,
      portfolio_id: sourceMode === "PORTFOLIO" ? portfolioId : null,
      method,
      start,
      end,
      asset_ids: selectedAssetIds,
      bounds: submittedBounds,
      baseline_weights: baseline,
      risk_free_rate_annual: parsedRiskFreeRate,
    };

    if (sourceMode === "PORTFOLIO" && !portfolioId) {
      setFormError("Select an owned portfolio before running portfolio-derived optimization.");
      return;
    }

    if (method === "EFFICIENT_FRONTIER") {
      const points = Number(frontierPoints);
      if (!Number.isInteger(points) || points < 2 || points > 100) {
        setFormError("Efficient-frontier points must be an integer from 2 through 100.");
        return;
      }
      request.frontier_points = points;
    }

    setFormError(null);
    try {
      const run = await createRun.mutateAsync(request);
      setActiveRunId(run.id);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Optimization request failed.");
    }
  }

  const header = (
    <DomainPageHeader
      eyebrow="Research workspace"
      title="Allocation Lab"
      description="Build a hypothetical universe or import an owned portfolio for server-authoritative optimization without mutating its ledger."
      actions={
        <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
          Server-authoritative optimization
        </span>
      }
    />
  );

  if (portfoliosQuery.isPending || assetCatalogQuery.isPending) {
    return (
      <DashboardShell header={header}>
        <div className="mx-auto w-full max-w-[1800px] px-4 pb-10 sm:px-6 lg:px-8">
          <LabSkeleton />
        </div>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell header={header}>
      <div className="mx-auto w-full max-w-[1800px] space-y-5 px-4 pb-10 sm:px-6 lg:px-8">
        <section
          className="rounded-2xl border border-blue-200 border-l-4 border-l-blue-500 bg-blue-50/70 p-5 shadow-sm sm:p-6"
          aria-labelledby="allocation-methodology-heading"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                Canonical analytical note
              </p>
              <h2
                id="allocation-methodology-heading"
                className="mt-1 text-lg font-semibold text-slate-950"
              >
                Methodology
              </h2>
              <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-700">
                These rules are fixed by the server-side optimization engine. They are shown
                here as read-only context so configuration choices remain distinct from the
                canonical mathematics used for every persisted run.
              </p>
            </div>
            <span className="rounded-full border border-blue-200 bg-white/80 px-3 py-1 text-xs font-semibold text-blue-800">
              Read-only methodology
            </span>
          </div>

          <dl className="mt-5 grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
            <div>
              <dt className="text-xs text-blue-700">Historical price field</dt>
              <dd className="mt-1 font-semibold text-slate-950">adjusted_close</dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Annualization factor</dt>
              <dd className="mt-1 font-semibold text-slate-950">252</dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Expected returns</dt>
              <dd className="mt-1 font-semibold text-slate-950">
                Mean daily simple return × 252
              </dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Covariance</dt>
              <dd className="mt-1 font-semibold text-slate-950">
                Complete-case sample covariance, ddof=1 × 252
              </dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Position policy</dt>
              <dd className="mt-1 font-semibold text-slate-950">
                Long-only · unlevered · fully invested
              </dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Provider</dt>
              <dd className="mt-1 font-semibold text-slate-950">
                {activeRun?.provenance.provider ?? "Server-configured at execution"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Engine version</dt>
              <dd className="mt-1 font-semibold text-slate-950">
                {activeRun?.provenance.engine_version ?? "Recorded on every run"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-blue-700">Method version</dt>
              <dd className="mt-1 font-semibold text-slate-950">
                {activeRun?.provenance.method_version ?? "Recorded on every run"}
              </dd>
            </div>
          </dl>
        </section>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] xl:items-start">
          <section className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-950">Allocation source</h2>
          <p className="mt-1 text-sm text-slate-600">
            Ad hoc analysis does not create a real portfolio. Existing-portfolio import is read-only.
          </p>

          <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Allocation source mode">
            <button
              type="button"
              aria-pressed={sourceMode === "AD_HOC"}
              onClick={() => updateSourceMode("AD_HOC")}
              className={`rounded-lg border px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                sourceMode === "AD_HOC"
                  ? "border-blue-300 bg-blue-50 text-blue-900"
                  : "border-slate-200 bg-white text-slate-700"
              }`}
            >
              Ad hoc portfolio
            </button>
            <button
              type="button"
              aria-pressed={sourceMode === "PORTFOLIO"}
              onClick={() => updateSourceMode("PORTFOLIO")}
              className={`rounded-lg border px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                sourceMode === "PORTFOLIO"
                  ? "border-blue-300 bg-blue-50 text-blue-900"
                  : "border-slate-200 bg-white text-slate-700"
              }`}
            >
              Existing portfolio
            </button>
          </div>

          {sourceMode === "PORTFOLIO" ? (
            <div className="mt-5 flex flex-wrap items-end gap-3">
              <label className="block min-w-64 text-xs font-semibold text-slate-700">
                Owned portfolio
                <select
                  value={portfolioId}
                  onChange={(event) => updatePortfolio(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  <option value="">Select portfolio</option>
                  {(portfoliosQuery.data ?? []).map((portfolio) => (
                    <option key={portfolio.id} value={portfolio.id}>
                      {portfolio.name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={!portfolioId || snapshotQuery.isPending}
                onClick={importPortfolioHoldings}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
              >
                {snapshotQuery.isPending ? "Loading holdings…" : "Import current holdings"}
              </button>
              {selectedPortfolio ? (
                <Link
                  to={`/portfolios/${encodeURIComponent(selectedPortfolio.id)}/dashboard${
                    isDashboardRange(rangeParam)
                      ? `?range=${encodeURIComponent(rangeParam)}`
                      : ""
                  }`}
                  className="pb-2 text-sm font-semibold text-blue-700 underline underline-offset-4"
                >
                  Open portfolio dashboard
                </Link>
              ) : null}
            </div>
          ) : (
            <form className="mt-5" onSubmit={addSymbols}>
              <label htmlFor="allocation-symbols" className="text-xs font-semibold text-slate-700">
                Add ticker symbols
              </label>
              <div className="mt-1 flex flex-col gap-2 sm:flex-row">
                <input
                  id="allocation-symbols"
                  value={symbolInput}
                  onChange={(event) => setSymbolInput(event.target.value)}
                  placeholder="AAPL, MSFT, QQQ"
                  className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm uppercase outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={resolveAssetsMutation.isPending}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
                >
                  {resolveAssetsMutation.isPending ? "Resolving…" : "Add canonical assets"}
                </button>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Symbols are resolved through the server's canonical asset/discovery boundary.
              </p>
            </form>
          )}

          {assetMessage ? (
            <p className="mt-3 text-sm text-slate-700" role="status">
              {assetMessage}
            </p>
          ) : null}
        </section>

          <form className="min-w-0" onSubmit={submitOptimization}>
            <section className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <h2 className="text-lg font-semibold text-slate-950">Configuration</h2>
              <p className="mt-1 text-sm text-slate-600">
                These are supported user-controlled inputs. Canonical methodology is summarized in the note above.
              </p>

              <div className="mt-5 grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
              <label className="block text-xs font-semibold text-slate-700">
                Analysis start
                <input
                  type="date"
                  value={start}
                  onChange={(event) => setStart(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                />
              </label>
              <label className="block text-xs font-semibold text-slate-700">
                End (exclusive)
                <input
                  type="date"
                  value={end}
                  onChange={(event) => setEnd(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                />
              </label>
              <label className="block text-xs font-semibold text-slate-700">
                Optimization method
                <select
                  value={method}
                  onChange={(event) =>
                    setMethod(event.target.value as OptimizationRunMethod)
                  }
                  className="mt-1 block w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-normal outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  {METHOD_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs font-semibold text-slate-700">
                Annual risk-free rate
                <input
                  type="number"
                  step="0.0001"
                  value={riskFreeRate}
                  onChange={(event) => setRiskFreeRate(event.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                />
              </label>
              {method === "EFFICIENT_FRONTIER" ? (
                <label className="block text-xs font-semibold text-slate-700">
                  Frontier points
                  <input
                    type="number"
                    min={2}
                    max={100}
                    step={1}
                    value={frontierPoints}
                    onChange={(event) => setFrontierPoints(event.target.value)}
                    className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  />
                </label>
              ) : null}
            </div>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[820px] border-collapse text-left text-sm">
                <caption className="sr-only">
                  Optimization universe, baseline weights, and per-asset bounds.
                </caption>
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th className="py-2 pr-4 font-semibold">Asset</th>
                    <th className="py-2 pr-4 font-semibold">
                      {sourceMode === "AD_HOC" ? "Custom baseline" : "Observed current"}
                    </th>
                    <th className="py-2 pr-4 font-semibold">Minimum weight</th>
                    <th className="py-2 pr-4 font-semibold">Maximum weight</th>
                    <th className="py-2 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedAssets.map((item) => {
                    const observed =
                      sourceMode === "PORTFOLIO"
                        ? currentHoldingWeightByAsset.get(item.asset.id) ?? null
                        : null;
                    return (
                      <tr key={item.asset.id} className="border-b border-slate-100">
                        <th className="py-3 pr-4">
                          <span className="font-semibold text-slate-950">{item.asset.symbol}</span>
                          <span className="ml-2 font-normal text-slate-500">{item.asset.name}</span>
                        </th>
                        <td className="py-3 pr-4">
                          {sourceMode === "AD_HOC" ? (
                            <input
                              aria-label={`${item.asset.symbol} baseline weight`}
                              type="number"
                              min="0"
                              max="1"
                              step="0.01"
                              value={item.baseline}
                              onChange={(event) =>
                                updateAssetControl(
                                  item.asset.id,
                                  "baseline",
                                  event.target.value,
                                )
                              }
                              placeholder="optional"
                              className="w-28 rounded-lg border border-slate-200 px-2 py-1.5 tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            />
                          ) : (
                            <span className="tabular-nums">{formatPercent(observed)}</span>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <input
                            aria-label={`${item.asset.symbol} minimum weight`}
                            type="number"
                            min="0"
                            max="1"
                            step="0.01"
                            value={item.minimum}
                            onChange={(event) =>
                              updateAssetControl(
                                item.asset.id,
                                "minimum",
                                event.target.value,
                              )
                            }
                            className="w-28 rounded-lg border border-slate-200 px-2 py-1.5 tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                          />
                        </td>
                        <td className="py-3 pr-4">
                          <input
                            aria-label={`${item.asset.symbol} maximum weight`}
                            type="number"
                            min="0"
                            max="1"
                            step="0.01"
                            value={item.maximum}
                            onChange={(event) =>
                              updateAssetControl(
                                item.asset.id,
                                "maximum",
                                event.target.value,
                              )
                            }
                            className="w-28 rounded-lg border border-slate-200 px-2 py-1.5 tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                          />
                        </td>
                        <td className="py-3">
                          <button
                            type="button"
                            onClick={() => removeAsset(item.asset.id)}
                            className="font-semibold text-rose-700 outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {selectedAssets.length === 0 ? (
              <div className="mt-4">
                <StatePanel
                  title="No assets selected"
                  message={
                    sourceMode === "AD_HOC"
                      ? "Add canonical stock/ETF symbols to build a hypothetical optimization universe."
                      : "Select a portfolio and import its current eligible holdings."
                  }
                />
              </div>
            ) : null}

            {formError ? (
              <p className="mt-4 text-sm font-medium text-rose-700" role="alert">
                {formError}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={createRun.isPending || selectedAssets.length === 0}
              className="mt-5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white outline-none hover:bg-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-50"
            >
              {createRun.isPending ? "Running optimization…" : "Run optimization"}
            </button>
            </section>
          </form>
        </div>

        {createRun.error instanceof Error ? (
          <StatePanel
            title={errorTitle(createRun.error)}
            message={createRun.error.message}
            tone="error"
          />
        ) : null}

        {activeRun ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                  Persisted run
                </p>
                <h2 className="mt-1 text-lg font-semibold text-slate-950">
                  {METHOD_OPTIONS.find((item) => item.value === activeRun.method)?.label ??
                    activeRun.method}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {runSourceLabel(activeRun)}
                </p>
              </div>
              <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold">
                {statusLabel(activeRun.status)}
              </span>
            </div>

            {activeRun.status === "FAILED" ? (
              <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
                <strong>{activeRun.failure_code || "OPTIMIZATION_FAILED"}</strong>
                <p className="mt-1">{activeRun.failure_message || "Optimization failed."}</p>
              </div>
            ) : null}

            {activeRun.status === "PENDING" || activeRun.status === "RUNNING" ? (
              <p className="mt-4 text-sm text-slate-600" role="status">
                The persisted run is {activeRun.status.toLowerCase()}. This page will poll the
                run resource until it reaches a terminal state.
              </p>
            ) : null}

            {activeRun.status === "SUCCEEDED" && activeRun.result?.portfolio ? (
              <dl className="mt-5 grid gap-4 sm:grid-cols-3">
                <div>
                  <dt className="text-xs text-slate-500">Expected annual return</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums">
                    {formatPercent(activeRun.result.portfolio.expected_return)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Expected annual volatility</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums">
                    {formatPercent(activeRun.result.portfolio.expected_volatility)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Sharpe ratio</dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums">
                    {formatRatio(activeRun.result.portfolio.sharpe_ratio)}
                  </dd>
                </div>
              </dl>
            ) : null}

            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-xs text-slate-500">Period</dt>
                <dd className="mt-1 font-medium">
                  {activeRun.provenance.period_start} to{" "}
                  {activeRun.provenance.period_end_exclusive} (end exclusive)
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Risk-free rate</dt>
                <dd className="mt-1 font-medium tabular-nums">
                  {formatPercent(activeRun.provenance.risk_free_rate_annual)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Price field</dt>
                <dd className="mt-1 font-medium">{activeRun.provenance.price_field}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Data fingerprint</dt>
                <dd className="mt-1 break-all font-mono text-xs">
                  {activeRun.provenance.data_fingerprint || "Not available"}
                </dd>
              </div>
            </dl>

            {activeRun.warnings.length > 0 ? (
              <ul className="mt-4 space-y-1 text-sm text-amber-900">
                {activeRun.warnings.map((warning) => (
                  <li key={`${warning.code}-${warning.message}`}>
                    <strong>{warning.code}</strong>: {warning.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ) : null}

        {selectedAssets.length > 0 ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold text-slate-950">
              Allocation comparison
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Optimized columns appear only when a matching successful persisted run exists.
            </p>
            <div className="mt-4">
              <AllocationComparisonChart
                rows={comparisonRows}
                baselineLabel={
                  sourceMode === "AD_HOC" ? "Custom baseline" : "Current observed"
                }
              />
            </div>
          </section>
        ) : null}

        {(frontierRun?.result?.frontier.length ?? 0) > 0 ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold text-slate-950">Efficient frontier</h2>
            <p className="mt-1 text-sm text-slate-600">
              Every plotted point is returned by the server. No interpolation is performed.
            </p>
            <div className="mt-4">
              <EfficientFrontierChart
                points={frontierRun!.result!.frontier}
                assetLabels={assetLabels}
              />
            </div>
          </section>
        ) : null}

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-950">Run history</h2>
          <p className="mt-1 text-sm text-slate-600">
            Previous ad hoc and portfolio-derived runs remain immutable and auditable.
          </p>

          {runsQuery.isPending ? (
            <Skeleton className="mt-4 h-32 w-full" />
          ) : runsQuery.error instanceof Error ? (
            <div className="mt-4">
              <StatePanel
                title="Optimization run history could not load"
                message={runsQuery.error.message}
                tone="error"
              />
            </div>
          ) : (runsQuery.data ?? []).length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">No persisted optimization runs yet.</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th className="py-2 pr-4 font-semibold">Source</th>
                    <th className="py-2 pr-4 font-semibold">Method</th>
                    <th className="py-2 pr-4 font-semibold">Period</th>
                    <th className="py-2 pr-4 font-semibold">Status</th>
                    <th className="py-2 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(runsQuery.data ?? []).slice(0, 20).map((run) => (
                    <tr key={run.id} className="border-b border-slate-100">
                      <td className="py-2 pr-4">{runSourceLabel(run)}</td>
                      <td className="py-2 pr-4">{run.method}</td>
                      <td className="py-2 pr-4">
                        {run.provenance.period_start} → {run.provenance.period_end_exclusive}
                      </td>
                      <td className="py-2 pr-4">{statusLabel(run.status)}</td>
                      <td className="py-2">
                        <button
                          type="button"
                          onClick={() => setActiveRunId(run.id)}
                          className="font-semibold text-blue-700 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                        >
                          Inspect run
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </DashboardShell>
  );
}
