import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";

import { TransactionHistoryPanel } from "./TransactionHistoryPanel";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <TransactionHistoryPanel portfolioId={PORTFOLIO_ID} />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("TransactionHistoryPanel", () => {
  it("renders the complete read-only portfolio ledger using canonical asset identity", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        expect(String(input)).toBe(
          `/api/v1/portfolios/${PORTFOLIO_ID}/transactions/`,
        );
        return new Response(
          JSON.stringify([
            {
              id: "00000000-0000-0000-0000-000000000901",
              portfolio_id: PORTFOLIO_ID,
              transaction_type: "BUY",
              asset_id: "00000000-0000-0000-0000-000000000101",
              asset_symbol: "AAPL",
              occurred_at: "2020-01-03T15:30:00Z",
              source_sequence: 1,
              quantity: "10.000000000000",
              price: "300.00000000",
              fees: "1.00000000",
              cash_amount: null,
              created_at: "2026-09-18T14:00:00Z",
            },
            {
              id: "00000000-0000-0000-0000-000000000900",
              portfolio_id: PORTFOLIO_ID,
              transaction_type: "DEPOSIT",
              asset_id: null,
              asset_symbol: null,
              occurred_at: "2020-01-02T14:00:00Z",
              source_sequence: 1,
              quantity: null,
              price: null,
              fees: "0.00000000",
              cash_amount: "10000.00000000",
              created_at: "2026-09-18T14:00:00Z",
            },
          ]),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      }),
    );

    renderPanel();

    expect(
      await screen.findByRole("heading", { name: "Transaction history" }),
    ).toBeInTheDocument();

    const table = await screen.findByRole("table", {
      name: "Complete transaction history for the selected portfolio",
    });
    expect(within(table).getByText("AAPL")).toBeInTheDocument();
    expect(
      within(table).getByText("00000000-0000-0000-0000-000000000101"),
    ).toBeInTheDocument();
    expect(within(table).getByText("10,000")).toBeInTheDocument();
    expect(screen.getByLabelText("2 transactions")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reconcile/i })).not.toBeInTheDocument();
  });

  it("renders an explicit empty-ledger state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );

    renderPanel();

    expect(
      await screen.findByText("No transactions have been recorded for this portfolio yet."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("0 transactions")).toBeInTheDocument();
  });
});
