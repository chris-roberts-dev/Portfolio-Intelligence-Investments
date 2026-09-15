import {
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { Link, useLocation } from "react-router";

import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardMover,
  DashboardMoversResult,
} from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
  humanizeCode,
} from "./formatting";

type MoversTabKey =
  | "GAINERS"
  | "LOSERS"
  | "CONTRIBUTORS"
  | "DETRACTORS";

interface MoversPanelProps {
  movers: DashboardMoversResult | null;
  portfolioId: string;
  moduleError: string | null;
}

const TABS: ReadonlyArray<{
  key: MoversTabKey;
  label: string;
}> = [
  { key: "GAINERS", label: "Top Gainers" },
  { key: "LOSERS", label: "Top Losers" },
  { key: "CONTRIBUTORS", label: "Largest Contributors" },
  { key: "DETRACTORS", label: "Largest Detractors" },
];

function itemsForTab(
  movers: DashboardMoversResult,
  tab: MoversTabKey,
): DashboardMover[] {
  if (tab === "GAINERS") {
    return movers.top_gainers;
  }

  if (tab === "LOSERS") {
    return movers.top_losers;
  }

  if (tab === "CONTRIBUTORS") {
    return movers.largest_contributors;
  }

  return movers.largest_detractors;
}

function emptyMessage(tab: MoversTabKey): string {
  if (tab === "GAINERS") {
    return "No positive selected-period holding returns are available.";
  }

  if (tab === "LOSERS") {
    return "No negative selected-period holding returns are available.";
  }

  if (tab === "CONTRIBUTORS") {
    return "No positive selected-period return contributions are available.";
  }

  return "No negative selected-period return contributions are available.";
}

function primaryMetric(
  mover: DashboardMover,
  tab: MoversTabKey,
): number | null {
  return tab === "GAINERS" || tab === "LOSERS"
    ? mover.selected_period_return
    : mover.contribution_to_return;
}

function primaryMetricLabel(tab: MoversTabKey): string {
  return tab === "GAINERS" || tab === "LOSERS"
    ? "Selected-period return"
    : "Contribution to return";
}

function metricPresentation(value: number | null): {
  text: string;
  className: string;
} {
  if (value === null || !Number.isFinite(value)) {
    return {
      text: "Not available",
      className: "text-slate-500",
    };
  }

  if (value > 0) {
    return {
      text: `▲ ${formatPercent(value)}`,
      className: "text-emerald-700",
    };
  }

  if (value < 0) {
    return {
      text: `▼ ${formatPercent(value)}`,
      className: "text-rose-700",
    };
  }

  return {
    text: `• ${formatPercent(value)}`,
    className: "text-slate-700",
  };
}

function MoverCard({
  mover,
  tab,
  portfolioId,
}: {
  mover: DashboardMover;
  tab: MoversTabKey;
  portfolioId: string;
}) {
  const location = useLocation();
  const metric = primaryMetric(mover, tab);
  const presentation = metricPresentation(metric);
  const detailPath = `/portfolios/${encodeURIComponent(
    portfolioId,
  )}/holdings/${encodeURIComponent(mover.asset_id)}${location.search}`;

  return (
    <li data-testid="mover-card">
      <Link
        to={detailPath}
        state={{
          holding: {
            assetId: mover.asset_id,
            symbol: mover.symbol,
            name: mover.name,
            assetType: mover.asset_type,
            currency: mover.currency,
          },
        }}
        className="group block rounded-2xl border border-slate-200 bg-white p-4 outline-none transition hover:border-blue-200 hover:bg-blue-50/30 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        aria-label={`Open ${mover.symbol} holding details`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-950 group-hover:text-blue-700">
                {mover.symbol}
              </span>
              <DataQualityBadge quality={mover.data_quality} />
              {!mover.is_current_holding ? (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600">
                  Historical position
                </span>
              ) : null}
            </div>
            <p className="mt-1 truncate text-sm text-slate-600">
              {mover.name}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {mover.asset_type} · {mover.currency}
            </p>
          </div>

          <div className="shrink-0 text-right">
            <p className="text-xs font-medium text-slate-500">
              {primaryMetricLabel(tab)}
            </p>
            <p
              className={`mt-1 font-semibold tabular-nums ${presentation.className}`}
              data-mover-primary-metric={metric ?? undefined}
            >
              {presentation.text}
            </p>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-slate-500">Period return</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatPercent(mover.selected_period_return)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Contribution</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatPercent(mover.contribution_to_return)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Weight</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatPercent(mover.weight)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Current value</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatCurrency(mover.market_value, mover.currency)}
            </dd>
          </div>
        </dl>

        {mover.unavailable_reasons.length > 0 ? (
          <p className="mt-3 text-xs text-slate-500">
            {mover.unavailable_reasons
              .map((reason) => humanizeCode(reason))
              .filter((reason): reason is string => reason !== null)
              .join(" · ")}
          </p>
        ) : null}
      </Link>
    </li>
  );
}

function ReconciliationSummary({
  movers,
}: {
  movers: DashboardMoversResult;
}) {
  const reconciliation = movers.reconciliation;
  const unavailableReason = humanizeCode(reconciliation.unavailable_reason);

  return (
    <div
      className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
      aria-label="Return contribution reconciliation"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Attribution reconciliation
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {reconciliation.status === "AVAILABLE"
              ? `${reconciliation.periods} linked return periods`
              : unavailableReason ?? "Contribution attribution is unavailable."}
          </p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
            reconciliation.status === "AVAILABLE"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-800"
          }`}
        >
          {reconciliation.status === "AVAILABLE" ? "Reconciled" : "Unavailable"}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
        <div>
          <dt className="text-xs text-slate-500">Portfolio TWR</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-cumulative-return={reconciliation.cumulative_return ?? undefined}
          >
            {formatPercent(reconciliation.cumulative_return)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Asset contributions</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-asset-contribution-total={
              reconciliation.asset_contribution_total ?? undefined
            }
          >
            {formatPercent(reconciliation.asset_contribution_total)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Unattributed</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-unattributed-contribution={
              reconciliation.unattributed_contribution ?? undefined
            }
          >
            {formatPercent(reconciliation.unattributed_contribution)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Reconciliation error</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-reconciliation-error={
              reconciliation.reconciliation_error ?? undefined
            }
          >
            {formatPercent(reconciliation.reconciliation_error)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function MoversPanel({
  movers,
  portfolioId,
  moduleError,
}: MoversPanelProps) {
  const [activeTab, setActiveTab] = useState<MoversTabKey>("GAINERS");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  if (moduleError !== null) {
    return (
      <StatePanel
        title="Movers unavailable"
        message={moduleError}
        tone="error"
      />
    );
  }

  if (movers === null) {
    return (
      <StatePanel
        title="Movers unavailable"
        message="No mover rankings are available for this dashboard snapshot."
      />
    );
  }

  const activeIndex = TABS.findIndex((tab) => tab.key === activeTab);
  const activeItems = itemsForTab(movers, activeTab);

  function activateTab(index: number) {
    const tab = TABS[index];
    if (!tab) {
      return;
    }

    setActiveTab(tab.key);
    tabRefs.current[index]?.focus();
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      activateTab((activeIndex + 1) % TABS.length);
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      activateTab((activeIndex - 1 + TABS.length) % TABS.length);
      return;
    }

    if (event.key === "Home") {
      event.preventDefault();
      activateTab(0);
      return;
    }

    if (event.key === "End") {
      event.preventDefault();
      activateTab(TABS.length - 1);
    }
  }

  return (
    <DashboardCard
      title="Movers"
      eyebrow="Selected-period drivers"
      actions={<DataQualityBadge quality={movers.data_quality} />}
    >
      <p className="text-sm text-slate-600">
        Rankings are supplied in canonical server order with deterministic
        tie-breaking. React does not re-rank returns or contributions.
      </p>

      <div
        className="mt-5 flex gap-1 overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50 p-1"
        role="tablist"
        aria-label="Portfolio mover rankings"
      >
        {TABS.map((tab, index) => {
          const selected = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              ref={(node) => {
                tabRefs.current[index] = node;
              }}
              type="button"
              role="tab"
              id={`movers-tab-${tab.key.toLowerCase()}`}
              aria-controls="movers-tabpanel"
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveTab(tab.key)}
              onKeyDown={handleTabKeyDown}
              className={`shrink-0 rounded-xl px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                selected
                  ? "bg-slate-950 text-white"
                  : "text-slate-600 hover:bg-white hover:text-slate-950"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div
        id="movers-tabpanel"
        role="tabpanel"
        aria-labelledby={`movers-tab-${activeTab.toLowerCase()}`}
        className="mt-5"
      >
        {activeItems.length === 0 ? (
          <StatePanel
            title={TABS[activeIndex]?.label ?? "Movers"}
            message={emptyMessage(activeTab)}
          />
        ) : (
          <ol className="grid gap-3 lg:grid-cols-2" aria-label="Server-ranked movers">
            {activeItems.map((mover) => (
              <MoverCard
                key={mover.asset_id}
                mover={mover}
                tab={activeTab}
                portfolioId={portfolioId}
              />
            ))}
          </ol>
        )}
      </div>

      <div className="mt-5">
        <ReconciliationSummary movers={movers} />
      </div>

      {movers.warnings.length > 0 ? (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            Movers notes
          </p>
          <ul className="mt-2 space-y-1 text-sm text-amber-950">
            {movers.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
        <p>
          Period: {movers.provenance.effective_start} to {" "}
          {movers.provenance.effective_end_exclusive} · Provider: {" "}
          {movers.provenance.provider}
        </p>
        <p>
          Period data as of {formatDateTime(movers.provenance.period_data_as_of)} · {" "}
          Current prices as of {formatDateTime(movers.provenance.current_price_as_of)}
        </p>
        <p>
          Attribution: {movers.provenance.attribution_method} · Engine {" "}
          {movers.provenance.engine_version}
        </p>
      </div>
    </DashboardCard>
  );
}
