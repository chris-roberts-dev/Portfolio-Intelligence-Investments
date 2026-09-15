import {
  lazy,
  Suspense,
  useState,
} from "react";

import type {
  PerformanceChartMode,
} from "../../components/charts/PerformanceChart";
import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import type { DashboardPerformanceResult } from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
} from "./formatting";

const PerformanceChart = lazy(async () => {
  const module = await import(
    "../../components/charts/PerformanceChart"
  );

  return {
    default: module.PerformanceChart,
  };
});

interface PerformanceHeroProps {
  performance: DashboardPerformanceResult | null;
  currency: string;
  moduleError: string | null;
}

function signedTone(value: number | null): string {
  if (value === null || value === 0) {
    return "text-slate-700";
  }

  return value > 0 ? "text-emerald-700" : "text-rose-700";
}

export function PerformanceHero({
  performance,
  currency,
  moduleError,
}: PerformanceHeroProps) {
  const [mode, setMode] = useState<PerformanceChartMode>("VALUE");

  return (
    <DashboardCard
      title="Portfolio performance"
      eyebrow="Overview"
      className="min-h-136"
      actions={
        performance ? (
          <div className="flex items-center gap-2">
            <DataQualityBadge quality={performance.portfolio_data_quality} />
            <div
              className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1"
              aria-label="Performance chart view"
            >
              {(["VALUE", "RETURN"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setMode(option)}
                  aria-pressed={mode === option}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    mode === option
                      ? "bg-white text-slate-950 shadow-sm"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  {option === "VALUE" ? "Value" : "Return"}
                </button>
              ))}
            </div>
          </div>
        ) : undefined
      }
    >
      {performance === null ? (
        <StatePanel
          title="Performance unavailable"
          message={
            moduleError ??
            "The portfolio performance module did not return a usable result."
          }
          tone="error"
        />
      ) : performance.points.length === 0 ? (
        <StatePanel
          title="No performance history"
          message="There are no portfolio valuation points for the selected period."
        />
      ) : (
        <div>
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-slate-500">
                Current portfolio value
              </p>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
                {formatCurrency(performance.summary.ending_value, currency)}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <span
                  className={`font-semibold ${signedTone(
                    performance.summary.cumulative_return,
                  )}`}
                >
                  {formatPercent(performance.summary.cumulative_return)} TWR
                </span>
                <span className="text-slate-500">
                  Investment gain/loss {" "}
                  {formatCurrency(
                    performance.summary.investment_gain_loss,
                    currency,
                  )}
                </span>
              </div>
            </div>

            <div className="text-right text-xs leading-5 text-slate-500">
              <p>
                Data as of {formatDateTime(performance.provenance.data_as_of)}
              </p>
              <p>
                Provider {performance.provenance.provider} · {performance.provenance.price_field}
              </p>
            </div>
          </div>

          <Suspense
            fallback={
              <div
                className="h-72 w-full animate-pulse rounded-2xl bg-slate-100 sm:h-80"
                role="status"
                aria-label="Loading performance chart"
              />
            }
          >
            <PerformanceChart
              performance={performance}
              currency={currency}
              mode={mode}
            />
          </Suspense>

          {performance.warnings.length > 0 ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <p className="font-semibold">Data-quality note</p>
              <p className="mt-1 leading-6">
                {performance.warnings[0]?.message}
                {performance.warnings.length > 1
                  ? ` (+${performance.warnings.length - 1} more)`
                  : ""}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </DashboardCard>
  );
}
