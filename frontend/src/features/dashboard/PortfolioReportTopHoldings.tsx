import { Link, useLocation } from "react-router";

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
  const location = useLocation();
  const topHoldings = [...(holdings?.holdings ?? [])]
    .sort((left, right) => (right.weight ?? -1) - (left.weight ?? -1))
    .slice(0, 5);

  function researchHref(assetId: string): string {
    if (!holdings) {
      return "#";
    }

    return `/portfolios/${encodeURIComponent(holdings.provenance.portfolio_id)}/holdings/${encodeURIComponent(assetId)}${location.search}`;
  }

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
                    <Link
                      to={researchHref(holding.asset_id)}
                      state={{
                        holding: {
                          assetId: holding.asset_id,
                          symbol: holding.symbol,
                          name: holding.name,
                          assetType: holding.asset_type,
                          currency: holding.currency,
                        },
                      }}
                      className="inline-flex flex-wrap items-baseline gap-x-1 rounded-sm outline-none hover:text-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500"
                      aria-label={`Research ${holding.symbol} holding`}
                    >
                      <span className="font-semibold">{holding.symbol}</span>
                      <span className="text-xs font-normal text-slate-500">· {holding.name}</span>
                    </Link>
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
