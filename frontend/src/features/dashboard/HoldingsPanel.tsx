import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router";

import { HoldingSparkline } from "../../components/charts/HoldingSparkline";
import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardHolding,
  DashboardHoldingsResult,
} from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
  humanizeCode,
} from "./formatting";

const HOLDINGS_PAGE_SIZE = 25;

type HoldingsSortKey =
  | "MARKET_VALUE"
  | "WEIGHT"
  | "RETURN"
  | "SYMBOL";
type HoldingsSortDirection = "ASC" | "DESC";

interface HoldingsPanelProps {
  holdings: DashboardHoldingsResult | null;
  currency: string;
  portfolioId: string;
  moduleError: string | null;
}

function compareText(left: string, right: string): number {
  if (left === right) {
    return 0;
  }

  return left < right ? -1 : 1;
}

function normalizedDecimalParts(value: string): {
  sign: number;
  integer: string;
  fraction: string;
} {
  const trimmed = value.trim();
  const sign = trimmed.startsWith("-") ? -1 : 1;
  const unsigned = trimmed.replace(/^[+-]/, "");
  const [rawInteger = "0", rawFraction = ""] = unsigned.split(".", 2);
  const integer = rawInteger.replace(/^0+(?=\d)/, "") || "0";
  const fraction = rawFraction.replace(/0+$/, "");

  return { sign, integer, fraction };
}

function compareDecimalStrings(left: string, right: string): number {
  const a = normalizedDecimalParts(left);
  const b = normalizedDecimalParts(right);

  if (a.sign !== b.sign) {
    return a.sign < b.sign ? -1 : 1;
  }

  const magnitudeSign = a.sign;

  if (a.integer.length !== b.integer.length) {
    return a.integer.length < b.integer.length
      ? -1 * magnitudeSign
      : 1 * magnitudeSign;
  }

  const integerComparison = compareText(a.integer, b.integer);
  if (integerComparison !== 0) {
    return integerComparison * magnitudeSign;
  }

  const fractionLength = Math.max(a.fraction.length, b.fraction.length);
  const fractionComparison = compareText(
    a.fraction.padEnd(fractionLength, "0"),
    b.fraction.padEnd(fractionLength, "0"),
  );

  return fractionComparison * magnitudeSign;
}

function nullableComparison<T>(
  left: T | null,
  right: T | null,
  compare: (a: T, b: T) => number,
): number {
  if (left === null && right === null) {
    return 0;
  }

  if (left === null) {
    return 1;
  }

  if (right === null) {
    return -1;
  }

  return compare(left, right);
}

function compareHoldingMetric(
  left: DashboardHolding,
  right: DashboardHolding,
  sortKey: HoldingsSortKey,
): number {
  if (sortKey === "SYMBOL") {
    return compareText(left.symbol.toUpperCase(), right.symbol.toUpperCase());
  }

  if (sortKey === "MARKET_VALUE") {
    return nullableComparison(
      left.market_value,
      right.market_value,
      compareDecimalStrings,
    );
  }

  const leftValue =
    sortKey === "WEIGHT" ? left.weight : left.selected_period_return;
  const rightValue =
    sortKey === "WEIGHT" ? right.weight : right.selected_period_return;

  return nullableComparison(leftValue, rightValue, (a, b) => a - b);
}

function metricIsUnavailable(
  holding: DashboardHolding,
  sortKey: HoldingsSortKey,
): boolean {
  if (sortKey === "SYMBOL") {
    return false;
  }

  if (sortKey === "MARKET_VALUE") {
    return holding.market_value === null;
  }

  return sortKey === "WEIGHT"
    ? holding.weight === null
    : holding.selected_period_return === null;
}

function sortedHoldings(
  holdings: DashboardHolding[],
  sortKey: HoldingsSortKey,
  direction: HoldingsSortDirection,
): DashboardHolding[] {
  return [...holdings].sort((left, right) => {
    const leftUnavailable = metricIsUnavailable(left, sortKey);
    const rightUnavailable = metricIsUnavailable(right, sortKey);

    if (leftUnavailable !== rightUnavailable) {
      return leftUnavailable ? 1 : -1;
    }

    const metricComparison = compareHoldingMetric(left, right, sortKey);

    if (metricComparison !== 0) {
      return direction === "ASC" ? metricComparison : -metricComparison;
    }

    const symbolComparison = compareText(
      left.symbol.toUpperCase(),
      right.symbol.toUpperCase(),
    );

    if (symbolComparison !== 0) {
      return symbolComparison;
    }

    return compareText(left.asset_id, right.asset_id);
  });
}

function initials(symbol: string): string {
  return symbol.slice(0, 2).toUpperCase();
}

function movementPresentation(value: number | null): {
  label: string;
  className: string;
} {
  if (value === null) {
    return {
      label: "Not available",
      className: "text-slate-500",
    };
  }

  if (value > 0) {
    return {
      label: `▲ ${formatPercent(value)}`,
      className: "text-emerald-700",
    };
  }

  if (value < 0) {
    return {
      label: `▼ ${formatPercent(value)}`,
      className: "text-rose-700",
    };
  }

  return {
    label: `• ${formatPercent(value)}`,
    className: "text-slate-700",
  };
}

function HoldingRow({
  holding,
  currency,
  portfolioId,
}: {
  holding: DashboardHolding;
  currency: string;
  portfolioId: string;
}) {
  const location = useLocation();
  const movement = movementPresentation(holding.selected_period_return);
  const detailPath = `/portfolios/${encodeURIComponent(
    portfolioId,
  )}/holdings/${encodeURIComponent(holding.asset_id)}${location.search}`;
  const returnReason = humanizeCode(
    holding.selected_period_return_unavailable_reason,
  );
  const weightReason = humanizeCode(holding.weight_unavailable_reason);

  return (
    <li>
      <Link
        to={detailPath}
        state={{
          holding: {
            assetId: holding.asset_id,
            symbol: holding.symbol,
            name: holding.name,
            assetType: holding.asset_type,
            currency: holding.currency,
          },
        }}
        className="group grid gap-3 rounded-2xl border border-transparent px-3 py-4 outline-none transition hover:border-blue-100 hover:bg-blue-50/40 focus-visible:border-blue-300 focus-visible:ring-2 focus-visible:ring-blue-500 md:grid-cols-[minmax(12rem,1.4fr)_minmax(7rem,0.8fr)_minmax(7rem,0.8fr)_minmax(6rem,0.65fr)_minmax(7rem,0.7fr)_minmax(8rem,0.9fr)] md:items-center"
        aria-label={`Open ${holding.symbol} holding details`}
      >
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-700"
            aria-hidden="true"
          >
            {initials(holding.symbol)}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-950 group-hover:text-blue-700">
                {holding.symbol}
              </span>
              <DataQualityBadge quality={holding.data_quality} />
            </div>
            <p className="truncate text-sm text-slate-600">{holding.name}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {holding.asset_type} · {holding.currency}
            </p>
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">Price</p>
          <p
            className="font-medium tabular-nums text-slate-950"
            title={
              holding.current_price === null
                ? undefined
                : `Exact price: ${holding.current_price} ${holding.currency}`
            }
          >
            {formatCurrency(holding.current_price, holding.currency)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {formatDateTime(holding.current_price_retrieved_at)}
          </p>
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">Value</p>
          <p
            className="font-medium tabular-nums text-slate-950"
            title={
              holding.market_value === null
                ? undefined
                : `Exact market value: ${holding.market_value} ${currency}`
            }
          >
            {formatCurrency(holding.market_value, currency)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            Qty {holding.quantity}
          </p>
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">Weight</p>
          <p
            className="font-medium tabular-nums text-slate-950"
            title={
              holding.weight === null
                ? undefined
                : `Exact weight: ${holding.weight}`
            }
          >
            {formatPercent(holding.weight)}
          </p>
          {holding.weight === null && weightReason ? (
            <p className="mt-0.5 text-xs text-slate-500">{weightReason}</p>
          ) : null}
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">
            Selected-period return
          </p>
          <p className={`font-semibold tabular-nums ${movement.className}`}>
            {movement.label}
          </p>
          {holding.selected_period_return === null && returnReason ? (
            <p className="mt-0.5 text-xs text-slate-500">{returnReason}</p>
          ) : null}
        </div>

        <div>
          <p className="mb-1 text-xs font-medium text-slate-500 md:hidden">
            Price trend
          </p>
          <HoldingSparkline
            points={holding.sparkline}
            symbol={holding.symbol}
            currency={holding.currency}
          />
        </div>
      </Link>
    </li>
  );
}

export function HoldingsPanel({
  holdings,
  currency,
  portfolioId,
  moduleError,
}: HoldingsPanelProps) {
  const [sortKey, setSortKey] = useState<HoldingsSortKey>("MARKET_VALUE");
  const [direction, setDirection] = useState<HoldingsSortDirection>("DESC");
  const [page, setPage] = useState(0);

  const ordered = useMemo(
    () =>
      holdings === null
        ? []
        : sortedHoldings(holdings.holdings, sortKey, direction),
    [direction, holdings, sortKey],
  );
  const pageCount = Math.max(1, Math.ceil(ordered.length / HOLDINGS_PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const visibleHoldings = ordered.slice(
    safePage * HOLDINGS_PAGE_SIZE,
    (safePage + 1) * HOLDINGS_PAGE_SIZE,
  );

  return (
    <DashboardCard
      title="Holdings"
      eyebrow="Portfolio drivers"
      actions={
        holdings ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <DataQualityBadge quality={holdings.data_quality} />
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <span>Sort</span>
              <select
                value={sortKey}
                onChange={(event) => {
                  setSortKey(event.target.value as HoldingsSortKey);
                  setPage(0);
                }}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-800 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                aria-label="Sort holdings by"
              >
                <option value="MARKET_VALUE">Market value</option>
                <option value="WEIGHT">Weight</option>
                <option value="RETURN">Selected return</option>
                <option value="SYMBOL">Symbol</option>
              </select>
            </label>
            <button
              type="button"
              onClick={() => {
                setDirection((current) => (current === "ASC" ? "DESC" : "ASC"));
                setPage(0);
              }}
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
              aria-label={
                direction === "ASC"
                  ? "Sort holdings descending"
                  : "Sort holdings ascending"
              }
            >
              {direction === "ASC" ? "↑ Asc" : "↓ Desc"}
            </button>
          </div>
        ) : undefined
      }
    >
      {holdings === null ? (
        <StatePanel
          title="Holdings unavailable"
          message={
            moduleError ??
            "The dashboard snapshot did not return a usable holdings result."
          }
          tone="error"
        />
      ) : holdings.holdings.length === 0 ? (
        <StatePanel
          title="No current holdings"
          message="This portfolio has no open security positions at the snapshot cutoff."
        />
      ) : (
        <div>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3 text-xs text-slate-500">
            <p>
              {holdings.holdings.length} holding
              {holdings.holdings.length === 1 ? "" : "s"} · Current prices as of {" "}
              {formatDateTime(holdings.provenance.current_price_as_of)}
            </p>
            <p>
              Historical prices: {holdings.provenance.period_price_field} · {" "}
              {formatDateTime(holdings.provenance.period_data_as_of)}
            </p>
          </div>

          <div
            className="hidden grid-cols-[minmax(12rem,1.4fr)_minmax(7rem,0.8fr)_minmax(7rem,0.8fr)_minmax(6rem,0.65fr)_minmax(7rem,0.7fr)_minmax(8rem,0.9fr)] gap-3 border-b border-slate-200 px-3 pb-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:grid"
            aria-hidden="true"
          >
            <span>Security</span>
            <span>Price</span>
            <span>Value</span>
            <span>Weight</span>
            <span>Return</span>
            <span>Trend</span>
          </div>

          <ul className="divide-y divide-slate-100" aria-label="Portfolio holdings">
            {visibleHoldings.map((holding) => (
              <HoldingRow
                key={holding.asset_id}
                holding={holding}
                currency={currency}
                portfolioId={portfolioId}
              />
            ))}
          </ul>

          {pageCount > 1 ? (
            <nav
              className="mt-5 flex items-center justify-between gap-3 border-t border-slate-100 pt-4"
              aria-label="Holdings pages"
            >
              <p className="text-xs text-slate-500" aria-live="polite">
                Page {safePage + 1} of {pageCount}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={safePage === 0}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none disabled:cursor-not-allowed disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={safePage >= pageCount - 1}
                  onClick={() =>
                    setPage((current) => Math.min(pageCount - 1, current + 1))
                  }
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none disabled:cursor-not-allowed disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  Next
                </button>
              </div>
            </nav>
          ) : null}

          {holdings.warnings.length > 0 ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <p className="font-semibold">Holdings data-quality note</p>
              <p className="mt-1 leading-6">
                {holdings.warnings[0]?.message}
                {holdings.warnings.length > 1
                  ? ` (+${holdings.warnings.length - 1} more)`
                  : ""}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </DashboardCard>
  );
}
