import type { PortfolioAnalyticsResult } from "../../types/analytics";
import { formatPercent } from "./formatting";

interface PortfolioReportRiskProps {
  analytics: PortfolioAnalyticsResult | null;
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

export function PortfolioReportRisk({ analytics }: PortfolioReportRiskProps) {
  const rows = [
    {
      metric: "Sharpe ratio",
      value: ratio(analytics?.sharpe?.value ?? null),
      detail: analytics?.sharpe ? `${analytics.sharpe.observations} observations` : "Insufficient or unavailable history",
    },
    {
      metric: "Sortino ratio",
      value: ratio(analytics?.sortino?.value ?? null),
      detail: analytics?.sortino ? `${analytics.sortino.observations} observations` : "Insufficient or unavailable history",
    },
    {
      metric: "Portfolio beta",
      value: ratio(analytics?.beta?.value ?? null),
      detail: analytics?.beta ? `${analytics.beta.observations} benchmark-aligned observations` : "Benchmark relationship unavailable",
    },
    {
      metric: "Maximum drawdown",
      value: formatPercent(analytics?.maximum_drawdown?.value ?? null, 1),
      detail: analytics?.maximum_drawdown ? `${analytics.maximum_drawdown.observations} observations` : "Insufficient or unavailable history",
    },
    {
      metric: "Annualized volatility",
      value: formatPercent(analytics?.annualized_volatility ?? null, 1),
      detail: analytics ? `${analytics.observations} return observations` : "Insufficient or unavailable history",
    },
    {
      metric: "Largest position",
      value: formatPercent(analytics?.concentration?.largest_position_weight ?? null, 1),
      detail: analytics?.concentration ? `${analytics.concentration.security_position_count} security positions` : "Current allocation unavailable",
    },
  ];

  return (
    <section
      id="risk"
      className="portfolio-report-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-labelledby="portfolio-report-risk-heading"
    >
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-700">Risk</p>
        <h2 id="portfolio-report-risk-heading" className="mt-1 text-lg font-semibold text-slate-950">
          Risk metrics
        </h2>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Server-calculated metrics with observation counts; unavailable values remain explicit.
        </p>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase tracking-[0.08em] text-slate-500">
            <tr>
              <th scope="col" className="pb-2 font-semibold">Metric</th>
              <th scope="col" className="pb-2 text-right font-semibold">Current</th>
              <th scope="col" className="pb-2 pl-4 font-semibold">Calculation context</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.metric}>
                <th scope="row" className="py-2.5 font-medium text-slate-700">{row.metric}</th>
                <td className="py-2.5 text-right font-semibold tabular-nums text-slate-950">{row.value}</td>
                <td className="py-2.5 pl-4 text-xs text-slate-500">{row.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
