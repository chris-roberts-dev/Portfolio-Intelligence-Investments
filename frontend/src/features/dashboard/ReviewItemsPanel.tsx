import { useState } from "react";
import { Link, useLocation } from "react-router";

import { DashboardCard } from "../../components/ui/DashboardCard";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
    DashboardReviewItem,
    DashboardReviewItemsResult,
    ReviewItemCategory,
    ReviewItemSeverity,
} from "../../types/dashboard";
import { formatDate, formatDateTime, humanizeCode } from "./formatting";

interface ReviewItemsPanelProps {
  reviewItems: DashboardReviewItemsResult | null;
  isSnapshotComplete: boolean;
  moduleError: string | null;
}

interface ReviewFilterButtonProps {
  label: string;
  count: number;
  pressed: boolean;
  onClick: () => void;
}

function displayCode(value: string): string {
  return humanizeCode(value) ?? value;
}

function severityClasses(severity: ReviewItemSeverity): string {
  if (severity === "ERROR") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }

  if (severity === "WARNING") {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }

  return "border-blue-200 bg-blue-50 text-blue-800";
}

function severityIcon(severity: ReviewItemSeverity): string {
  if (severity === "ERROR") {
    return "!";
  }

  if (severity === "WARNING") {
    return "▲";
  }

  return "i";
}

function ReviewFilterButton({
  label,
  count,
  pressed,
  onClick,
}: ReviewFilterButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
        pressed
          ? "border-slate-900 bg-slate-950 text-white"
          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <span>{label}</span>
      <span
        className={`rounded-full px-1.5 py-0.5 tabular-nums ${
          pressed ? "bg-white/15 text-white" : "bg-slate-100 text-slate-600"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function ReviewItemCard({ item }: { item: DashboardReviewItem }) {
  const location = useLocation();
  const drilldown = item.drilldown;

  const holdingPath =
    drilldown.resource === "HOLDINGS" && drilldown.asset_id !== null
      ? `/portfolios/${encodeURIComponent(
          drilldown.portfolio_id,
        )}/holdings/${encodeURIComponent(drilldown.asset_id)}${location.search}`
      : null;

  return (
    <li
      className="rounded-2xl border border-slate-200 bg-white p-4"
      data-testid="review-item"
      data-review-item-key={item.key}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClasses(
                item.severity,
              )}`}
            >
              <span aria-hidden="true">{severityIcon(item.severity)}</span>
              {displayCode(item.severity)}
            </span>

            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
              {displayCode(item.category)}
            </span>
          </div>

          <p className="mt-3 text-sm font-semibold leading-6 text-slate-950">
            {item.message}
          </p>

          <p className="mt-1 text-xs text-slate-500">
            {displayCode(item.source)} · <code>{item.code}</code>
          </p>
        </div>

        {holdingPath !== null ? (
          <Link
            to={holdingPath}
            className="shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none transition hover:border-blue-200 hover:text-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Open holding
          </Link>
        ) : null}
      </div>

      <dl className="mt-4 grid gap-3 rounded-xl bg-slate-50 p-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="font-medium text-slate-500">Review resource</dt>
          <dd className="mt-1 font-semibold text-slate-900">
            {displayCode(drilldown.resource)}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Requested period</dt>
          <dd className="mt-1 text-slate-700">
            {drilldown.requested_start} to{" "}
            {drilldown.requested_end_exclusive} (end exclusive)
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Observation</dt>
          <dd className="mt-1 text-slate-700">
            {drilldown.observation_date ?? "Not available"}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Asset context</dt>
          <dd className="mt-1 text-slate-700">
            {drilldown.symbol ?? "Portfolio-level review item"}
          </dd>
        </div>

        <div className="sm:col-span-2 lg:col-span-4">
          <dt className="font-medium text-slate-500">Portfolio scope</dt>
          <dd className="mt-1 break-all font-mono text-[11px] text-slate-700">
            {drilldown.portfolio_id}
            {drilldown.asset_id !== null
              ? ` · asset ${drilldown.asset_id}`
              : ""}
          </dd>
        </div>
      </dl>
    </li>
  );
}

function ReviewItemsProvenance({
  reviewItems,
}: {
  reviewItems: DashboardReviewItemsResult;
}) {
  const provenance = reviewItems.provenance;

  return (
    <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
      <p>
        Requested period: {provenance.requested_start} to{" "}
        {provenance.requested_end_exclusive} (end exclusive) · Effective
        period: {provenance.effective_start} to{" "}
        {provenance.effective_end_exclusive} (end exclusive)
      </p>

      <p>
        Current data as of {formatDateTime(provenance.current_data_as_of)} ·
        Historical data as of{" "}
        {formatDateTime(provenance.historical_data_as_of)} · Analytics as of{" "}
        {formatDate(provenance.analytics_as_of_date)}
      </p>

      <p>
        Calculated {formatDateTime(provenance.calculated_at)} · Provider:{" "}
        {provenance.provider} · Engine: {provenance.engine_version} · Base
        currency: {provenance.base_currency}
      </p>

      <p>
        Sources: {provenance.included_sources.map(displayCode).join(" · ")}
      </p>

      <p className="break-all">
        Ordering: <code>{provenance.ordering_rule}</code>
      </p>
    </div>
  );
}

export function ReviewItemsPanel({
  reviewItems,
  isSnapshotComplete,
  moduleError,
}: ReviewItemsPanelProps) {
  const [severity, setSeverity] = useState<ReviewItemSeverity | null>(null);
  const [category, setCategory] = useState<ReviewItemCategory | null>(null);

  if (moduleError !== null) {
    return (
      <StatePanel
        title="Review items unavailable"
        message={moduleError}
        tone="error"
      />
    );
  }

  if (reviewItems === null) {
    return (
      <StatePanel
        title="Review items unavailable"
        message="No data-quality review-item module is available for this dashboard snapshot."
      />
    );
  }

  // Array.filter preserves the canonical server order.
  const visibleItems = reviewItems.items.filter(
    (item) =>
      (severity === null || item.severity === severity) &&
      (category === null || item.category === category),
  );

  const hasFilters = severity !== null || category !== null;

  return (
    <DashboardCard
      title="Data-quality review"
      eyebrow="Review items"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {!isSnapshotComplete ? (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
              Partial snapshot
            </span>
          ) : null}

          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
            {reviewItems.counts.total} review items
          </span>
        </div>
      }
    >
      <p className="text-sm leading-6 text-slate-600">
        Counts and item order come from the snapshot review-items contract.
        Filters only narrow the returned details; they do not create alerts,
        recompute server counts, or change canonical order.
      </p>

      {!isSnapshotComplete ? (
        <div
          className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          This dashboard snapshot is partial because another module is
          unavailable. The review-item module below remains available with its
          own calculation and data provenance.
        </div>
      ) : null}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <fieldset>
          <legend className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Severity
          </legend>

          <div className="mt-2 flex flex-wrap gap-2">
            <ReviewFilterButton
              label="All severities"
              count={reviewItems.counts.total}
              pressed={severity === null}
              onClick={() => setSeverity(null)}
            />

            {reviewItems.counts.by_severity.map((count) => (
              <ReviewFilterButton
                key={count.key}
                label={displayCode(count.key)}
                count={count.count}
                pressed={severity === count.key}
                onClick={() => setSeverity(count.key)}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Category
          </legend>

          <div className="mt-2 flex flex-wrap gap-2">
            <ReviewFilterButton
              label="All categories"
              count={reviewItems.counts.total}
              pressed={category === null}
              onClick={() => setCategory(null)}
            />

            {reviewItems.counts.by_category.map((count) => (
              <ReviewFilterButton
                key={count.key}
                label={displayCode(count.key)}
                count={count.count}
                pressed={category === count.key}
                onClick={() => setCategory(count.key)}
              />
            ))}
          </div>
        </fieldset>
      </div>

      {hasFilters ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
          <p aria-live="polite">
            Showing {visibleItems.length} of {reviewItems.counts.total}{" "}
            server-provided review items.
          </p>

          <button
            type="button"
            onClick={() => {
              setSeverity(null);
              setCategory(null);
            }}
            className="font-semibold text-blue-700 underline decoration-blue-200 underline-offset-4 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Clear review filters
          </button>
        </div>
      ) : null}

      <div className="mt-5">
        {reviewItems.counts.total === 0 ? (
          <StatePanel
            title="No review items"
            message="The current valuation, daily performance, and analytics sources reported no supported data-quality conditions for this selected period."
          />
        ) : visibleItems.length === 0 ? (
          <StatePanel
            title="No matching review items"
            message="No server-provided review items match the selected severity and category filters."
          />
        ) : (
          <ol
            className="space-y-3"
            aria-label="Data-quality review items"
          >
            {visibleItems.map((item) => (
              <ReviewItemCard key={item.key} item={item} />
            ))}
          </ol>
        )}
      </div>

      <ReviewItemsProvenance reviewItems={reviewItems} />
    </DashboardCard>
  );
}