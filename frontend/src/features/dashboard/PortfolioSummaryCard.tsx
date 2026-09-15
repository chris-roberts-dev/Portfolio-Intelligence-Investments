import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import {
  formatCurrency,
  formatDecimalPercent,
  humanizeCode,
} from "./formatting";
import type {
  DashboardPortfolioSummaryResult,
  PortfolioSummaryUnavailableReason,
} from "../../types/dashboard";

interface PortfolioSummaryCardProps {
  summary: DashboardPortfolioSummaryResult | null;
  currency: string;
  moduleError: string | null;
}

interface SummaryRowProps {
  label: string;
  value: string | null;
  reason?: PortfolioSummaryUnavailableReason | null;
  detail?: string | null;
}

function SummaryRow({ label, value, reason, detail }: SummaryRowProps) {
  return (
    <div className="border-b border-slate-100 py-3 last:border-0">
      <div className="flex items-start justify-between gap-4">
        <dt className="text-sm text-slate-600">{label}</dt>
        <dd className="text-right text-sm font-semibold text-slate-950">
          {value ?? "Not available"}
        </dd>
      </div>
      {reason ? (
        <p className="mt-1 text-right text-xs text-slate-500">
          {humanizeCode(reason)}
        </p>
      ) : detail ? (
        <p className="mt-1 text-right text-xs text-slate-500">{detail}</p>
      ) : null}
    </div>
  );
}

export function PortfolioSummaryCard({
  summary,
  currency,
  moduleError,
}: PortfolioSummaryCardProps) {
  return (
    <DashboardCard
      title="Portfolio summary"
      eyebrow="Accounting"
      actions={
        summary ? <DataQualityBadge quality={summary.data_quality} /> : undefined
      }
    >
      {summary === null ? (
        <StatePanel
          title="Summary unavailable"
          message={
            moduleError ??
            "The portfolio summary module did not return a usable result."
          }
          tone="error"
        />
      ) : (
        <dl>
          <SummaryRow
            label="Total market value"
            value={
              summary.metrics.total_market_value === null
                ? null
                : formatCurrency(summary.metrics.total_market_value, currency)
            }
            reason={summary.metrics.total_market_value_unavailable_reason}
          />
          <SummaryRow
            label="Net contributions"
            value={formatCurrency(summary.metrics.net_contributions, currency)}
          />
          <SummaryRow
            label="Cost basis"
            value={formatCurrency(summary.metrics.cost_basis, currency)}
            detail="Weighted-average analytical book cost"
          />
          <SummaryRow
            label="Cash balance"
            value={formatCurrency(summary.metrics.cash_balance, currency)}
            detail={
              summary.metrics.cash_percentage === null
                ? humanizeCode(summary.metrics.cash_percentage_unavailable_reason)
                : formatDecimalPercent(summary.metrics.cash_percentage)
            }
          />
          <SummaryRow
            label="Unrealized gain/loss"
            value={
              summary.metrics.unrealized_gain_loss === null
                ? null
                : formatCurrency(summary.metrics.unrealized_gain_loss, currency)
            }
            reason={summary.metrics.unrealized_gain_loss_unavailable_reason}
          />
          <SummaryRow
            label="Realized gain/loss"
            value={
              summary.metrics.selected_period_realized_gain_loss === null
                ? null
                : formatCurrency(
                    summary.metrics.selected_period_realized_gain_loss,
                    currency,
                  )
            }
            reason={
              summary.metrics.selected_period_realized_gain_loss_unavailable_reason
            }
          />
          <SummaryRow
            label="Income received"
            value={
              summary.metrics.selected_period_income_received === null
                ? null
                : formatCurrency(
                    summary.metrics.selected_period_income_received,
                    currency,
                  )
            }
            reason={summary.metrics.selected_period_income_unavailable_reason}
          />
        </dl>
      )}
    </DashboardCard>
  );
}
