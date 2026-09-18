import type { DashboardHoldingsResult } from "../../types/dashboard";
import { formatCurrency, formatPercent } from "./formatting";

interface PortfolioReportTopHoldingsProps {
  holdings: DashboardHoldingsResult | null;
  currency: string;
}

export function PortfolioReportTopHoldings({
  holdings,
  currency,
}: PortfolioReportTopHoldingsProps) {
  const topHoldings = [...(holdings?.holdings ?? [])]
    .sort((left, right) => (right.weight ?? -1) - (left.weight ?? -1))
    .slice(0, 5);

  return (
    <section
      id="holdings"
      className="portfolio-report-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-labelledby="portfolio-report-holdings-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-700">Holdings</p>
          <h2 id="portfolio-report-holdings-heading" className="mt-1 text-lg font-semibold text-slate-950">
            Top holdings
          </h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Highest current portfolio weights. Security return is distinct from contribution to portfolio return.
          </p>
        </div>
        <a
          href="#detailed-holdings"
          className="portfolio-report-screen-only text-xs font-semibold text-blue-700 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          View all holdings
        </a>
      </div>

      {topHoldings.length === 0 ? (
        <p className="mt-5 text-sm text-slate-500">No current security holdings are available.</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase tracking-[0.08em] text-slate-500">
              <tr>
                <th scope="col" className="pb-2 font-semibold">Asset</th>
                <th scope="col" className="pb-2 text-right font-semibold">Weight</th>
                <th scope="col" className="pb-2 text-right font-semibold">Value</th>
                <th scope="col" className="pb-2 text-right font-semibold">Return</th>
                <th scope="col" className="pb-2 text-right font-semibold">Contribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {topHoldings.map((holding) => (
                <tr key={holding.asset_id}>
                  <th scope="row" className="py-2.5 pr-4 font-medium text-slate-900">
                    <span className="font-semibold">{holding.symbol}</span>
                    <span className="ml-1 text-xs font-normal text-slate-500">· {holding.name}</span>
                  </th>
                  <td className="py-2.5 text-right tabular-nums text-slate-700">{formatPercent(holding.weight, 1)}</td>
                  <td className="py-2.5 text-right tabular-nums text-slate-700">{formatCurrency(holding.market_value, currency)}</td>
                  <td className="py-2.5 text-right tabular-nums text-slate-700">{formatPercent(holding.selected_period_return, 1)}</td>
                  <td className="py-2.5 text-right tabular-nums text-slate-700">{formatPercent(holding.contribution_to_return, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
