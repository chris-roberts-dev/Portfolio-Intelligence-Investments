import type { DashboardSnapshotResult } from "../../types/dashboard";
import { formatCurrency, formatPercent } from "./formatting";

interface PortfolioReportKpisProps {
  snapshot: DashboardSnapshotResult;
}

function valueTone(value: number | null): string {
  if (value === null || value === 0) {
    return "text-slate-950";
  }
  return value > 0 ? "text-emerald-700" : "text-rose-700";
}

function ratio(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function KpiCard({
  label,
  value,
  context,
  valueClassName = "text-slate-950",
}: {
  label: string;
  value: string;
  context: string;
  valueClassName?: string;
}) {
  return (
    <article className="portfolio-report-card rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-semibold text-slate-700">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tracking-tight tabular-nums ${valueClassName}`}>
        {value}
      </p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{context}</p>
    </article>
  );
}

export function PortfolioReportKpis({ snapshot }: PortfolioReportKpisProps) {
  const currency = snapshot.snapshot.base_currency;
  const totalValue = snapshot.summary?.metrics.total_market_value ?? null;
  const cumulativeReturn = snapshot.performance?.summary.cumulative_return ?? null;
  const benchmarkReturn =
    snapshot.performance?.summary.benchmark_cumulative_return ?? null;
  const cagr = snapshot.analytics?.cagr ?? null;
  const sharpe = snapshot.analytics?.sharpe ?? null;
  const volatility = snapshot.analytics?.annualized_volatility ?? null;

  return (
    <section
      id="report-summary"
      aria-label="Portfolio report key metrics"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"
    >
      <KpiCard
        label="Portfolio value"
        value={formatCurrency(totalValue, currency)}
        context="Current server-authoritative market value including eligible cash."
      />
      <KpiCard
        label="Cumulative return"
        value={formatPercent(cumulativeReturn, 1)}
        valueClassName={valueTone(cumulativeReturn)}
        context={`Benchmark ${formatPercent(benchmarkReturn, 1)} for the same reporting period.`}
      />
      <KpiCard
        label="CAGR"
        value={formatPercent(cagr?.value ?? null, 1)}
        valueClassName={valueTone(cagr?.value ?? null)}
        context={
          cagr
            ? `Compound annual growth rate · ${cagr.elapsed_days} elapsed days${
                cagr.is_short_period ? " · annualized short period" : ""
              }`
            : "Compound annual growth rate is not available for the selected period."
        }
      />
      <KpiCard
        label="Sharpe ratio"
        value={ratio(sharpe?.value ?? null)}
        context={
          sharpe
            ? `${sharpe.observations} return observations · risk-free rate ${formatPercent(sharpe.risk_free_rate_annual, 2)}`
            : "Not available for the selected period."
        }
      />
      <KpiCard
        label="Annualized volatility"
        value={formatPercent(volatility, 1)}
        context={
          snapshot.analytics
            ? `${snapshot.analytics.observations} return observations in the analytical window.`
            : "Not available for the selected period."
        }
      />
    </section>
  );
}
