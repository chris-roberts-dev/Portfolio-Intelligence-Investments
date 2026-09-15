import { Suspense, lazy } from "react";

import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { Skeleton } from "../../components/ui/Skeleton";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardAllocationGroup,
  DashboardAllocationResult,
} from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  humanizeCode,
} from "./formatting";

const AllocationChart = lazy(async () => {
  const module = await import("../../components/charts/AllocationChart");
  return { default: module.AllocationChart };
});

interface AllocationPanelProps {
  allocation: DashboardAllocationResult | null;
  currency: string;
  moduleError: string | null;
}

function formatWeight(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

function groupPositionLabel(group: DashboardAllocationGroup): string {
  if (group.is_cash) {
    return "Cash";
  }

  return `${group.asset_count} ${group.asset_count === 1 ? "holding" : "holdings"}`;
}

function AllocationChartSkeleton() {
  return (
    <div
      className="h-40 rounded-2xl bg-slate-50 p-4"
      role="status"
      aria-label="Loading allocation chart"
    >
      <Skeleton className="h-5 w-48" />
      <Skeleton className="mt-8 h-10 w-full rounded-lg" />
    </div>
  );
}

export function AllocationPanel({
  allocation,
  currency,
  moduleError,
}: AllocationPanelProps) {
  if (moduleError !== null) {
    return (
      <StatePanel
        title="Allocation unavailable"
        message={moduleError}
        tone="error"
      />
    );
  }

  if (allocation === null) {
    return (
      <StatePanel
        title="Allocation unavailable"
        message="No current allocation result is available for this dashboard snapshot."
      />
    );
  }

  const unsupportedReason = humanizeCode(allocation.unavailable_reason);
  const weightedGroups = allocation.groups.filter(
    (group) => group.weight !== null,
  );

  return (
    <section
      className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
      aria-labelledby="allocation-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Current portfolio
          </p>
          <h2
            id="allocation-heading"
            className="mt-1 text-xl font-semibold tracking-tight text-slate-950"
          >
            Allocation
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Backend-authoritative asset-class and cash weights.
          </p>
        </div>
        <DataQualityBadge quality={allocation.data_quality} />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500">Invested value</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatCurrency(allocation.totals.invested_value, currency)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {formatWeight(allocation.totals.invested_weight)} invested
          </p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500">Cash</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatCurrency(allocation.totals.cash_value, currency)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {formatWeight(allocation.totals.cash_weight)} of portfolio
          </p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500">Total value</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatCurrency(allocation.totals.total_market_value, currency)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            As of {formatDateTime(allocation.provenance.data_as_of)}
          </p>
        </div>
      </div>

      {!allocation.allocation_available ? (
        <div
          className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          <p className="font-semibold">Allocation weights are not available.</p>
          <p className="mt-1">
            {unsupportedReason ??
              "The backend could not produce authoritative current weights."}
          </p>
        </div>
      ) : null}

      {weightedGroups.length > 0 ? (
        <div className="mt-6">
          <Suspense fallback={<AllocationChartSkeleton />}>
            <AllocationChart groups={allocation.groups} currency={currency} />
          </Suspense>
        </div>
      ) : null}

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[34rem] border-separate border-spacing-0 text-left text-sm">
          <caption className="sr-only">
            Current portfolio allocation by asset class and cash
          </caption>
          <thead>
            <tr className="text-xs uppercase tracking-wide text-slate-500">
              <th scope="col" className="border-b border-slate-200 px-3 py-2 font-semibold">
                Group
              </th>
              <th scope="col" className="border-b border-slate-200 px-3 py-2 font-semibold">
                Positions
              </th>
              <th scope="col" className="border-b border-slate-200 px-3 py-2 text-right font-semibold">
                Market value
              </th>
              <th scope="col" className="border-b border-slate-200 px-3 py-2 text-right font-semibold">
                Weight
              </th>
            </tr>
          </thead>
          <tbody>
            {allocation.groups.map((group) => (
              <tr
                key={group.key}
                data-allocation-group-key={group.key}
                data-market-value={group.market_value}
                data-weight={group.weight ?? undefined}
                className="text-slate-700"
              >
                <th
                  scope="row"
                  className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950"
                >
                  {group.label}
                </th>
                <td className="border-b border-slate-100 px-3 py-3">
                  {groupPositionLabel(group)}
                </td>
                <td className="border-b border-slate-100 px-3 py-3 text-right font-medium text-slate-950">
                  {formatCurrency(group.market_value, currency)}
                </td>
                <td className="border-b border-slate-100 px-3 py-3 text-right font-medium text-slate-950">
                  {formatWeight(group.weight)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {allocation.warnings.length > 0 ? (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            Allocation notes
          </p>
          <ul className="mt-2 space-y-1 text-sm text-amber-950">
            {allocation.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
        <p>
          Grouping: {allocation.provenance.grouping_dimension.replaceAll("_", " ")} · Source:{" "}
          {allocation.provenance.grouping_source}
        </p>
        <p>
          Supported grouping dimensions:{" "}
          {allocation.provenance.supported_grouping_dimensions.join(", ")}
        </p>
        <p>
          Ordering: {allocation.provenance.ordering_rule} · Price field:{" "}
          {allocation.provenance.price_field}
        </p>
        <p>
          Other grouping: {allocation.provenance.other_grouping_applied ? "Applied" : "Not applied"}
          {allocation.provenance.other_grouping_threshold === null
            ? " · Threshold: none"
            : ` · Threshold: ${allocation.provenance.other_grouping_threshold}`}
        </p>
        <p>{allocation.provenance.other_grouping_rule}</p>
        <p>
          Allocation-to-holdings cross-filtering is not enabled yet. Stable group keys are preserved for a later explicit interaction contract.
        </p>
      </div>
    </section>
  );
}
