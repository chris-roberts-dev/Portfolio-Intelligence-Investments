import {
  DOMAIN_CARD_CLASS,
  DOMAIN_SECONDARY_ACTION_CLASS,
} from "../../components/ui/domainStyles";
import { usePortfolioTransactions } from "../../hooks/usePortfolioData";
import type { TransactionType } from "../../types/portfolioManagement";

function formatLedgerDecimal(value: string | null): string {
  if (value === null) {
    return "—";
  }

  const [rawInteger, rawFraction = ""] = value.split(".");
  const sign = rawInteger.startsWith("-") ? "-" : "";
  const integerDigits = sign ? rawInteger.slice(1) : rawInteger;
  const groupedInteger = integerDigits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fraction = rawFraction.replace(/0+$/, "");

  return fraction
    ? `${sign}${groupedInteger}.${fraction}`
    : `${sign}${groupedInteger}`;
}

function formatOccurredAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

const TRANSACTION_TYPE_LABELS: Record<TransactionType, string> = {
  DEPOSIT: "Deposit",
  WITHDRAWAL: "Withdrawal",
  BUY: "Buy",
  SELL: "Sell",
  DIVIDEND: "Dividend",
};

function transactionTypeLabel(type: TransactionType): string {
  return TRANSACTION_TYPE_LABELS[type];
}

interface TransactionHistoryPanelProps {
  portfolioId: string;
  description?: string;
}

export function TransactionHistoryPanel({
  portfolioId,
  description =
    "Every persisted ledger event for this portfolio, shown newest first. This is a read-only view of the server-authoritative transaction ledger.",
}: TransactionHistoryPanelProps) {
  const transactionsQuery = usePortfolioTransactions(portfolioId);
  const transactions = transactionsQuery.data ?? [];

  return (
    <section
      className={`${DOMAIN_CARD_CLASS} portfolio-report-card`}
      aria-labelledby="transaction-history-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2
            id="transaction-history-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Transaction history
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
            {description}
          </p>
        </div>
        {transactionsQuery.data !== undefined ? (
          <span
            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700"
            aria-label={`${transactions.length} transactions`}
          >
            {transactions.length} transaction{transactions.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>

      {transactionsQuery.isPending ? (
        <p className="mt-5 text-sm text-slate-500" role="status">
          Loading transaction history…
        </p>
      ) : transactionsQuery.error instanceof Error ? (
        <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4">
          <p className="text-sm text-rose-800" role="alert">
            Transaction history could not load: {transactionsQuery.error.message}
          </p>
          <button
            type="button"
            onClick={() => void transactionsQuery.refetch()}
            className={`mt-3 ${DOMAIN_SECONDARY_ACTION_CLASS}`}
          >
            Retry transaction history
          </button>
        </div>
      ) : transactions.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-600">
          No transactions have been recorded for this portfolio yet.
        </div>
      ) : (
        <div className="mt-5 overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full min-w-[1120px] border-collapse text-left text-sm">
            <caption className="sr-only">
              Complete transaction history for the selected portfolio
            </caption>
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                {[
                  "Occurred at",
                  "Type",
                  "Asset",
                  "Quantity",
                  "Price (USD)",
                  "Fees (USD)",
                  "Cash amount (USD)",
                  "Ledger ID",
                ].map((label) => (
                  <th key={label} scope="col" className="px-3 py-2.5 font-semibold">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {transactions.map((transaction) => (
                <tr
                  key={transaction.id}
                  className="border-t border-slate-100 align-top text-slate-700"
                >
                  <td className="whitespace-nowrap px-3 py-3">
                    <time dateTime={transaction.occurred_at}>
                      {formatOccurredAt(transaction.occurred_at)}
                    </time>
                  </td>
                  <td className="px-3 py-3 font-semibold text-slate-950">
                    {transactionTypeLabel(transaction.transaction_type)}
                  </td>
                  <td className="px-3 py-3">
                    {transaction.asset_symbol ? (
                      <div>
                        <span className="font-semibold text-slate-950">
                          {transaction.asset_symbol}
                        </span>
                        {transaction.asset_id ? (
                          <code className="mt-0.5 block break-all font-mono text-[11px] text-slate-500">
                            {transaction.asset_id}
                          </code>
                        ) : null}
                      </div>
                    ) : (
                      "Cash"
                    )}
                  </td>
                  <td className="px-3 py-3 tabular-nums">
                    {formatLedgerDecimal(transaction.quantity)}
                  </td>
                  <td className="px-3 py-3 tabular-nums">
                    {formatLedgerDecimal(transaction.price)}
                  </td>
                  <td className="px-3 py-3 tabular-nums">
                    {formatLedgerDecimal(transaction.fees)}
                  </td>
                  <td className="px-3 py-3 tabular-nums">
                    {formatLedgerDecimal(transaction.cash_amount)}
                  </td>
                  <td className="px-3 py-3">
                    <code className="break-all font-mono text-[11px] text-slate-600">
                      {transaction.id}
                    </code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
