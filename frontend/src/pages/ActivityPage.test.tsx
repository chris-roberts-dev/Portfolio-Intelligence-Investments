import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { ActivityPage } from "./ActivityPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const SECOND_PORTFOLIO_ID = "00000000-0000-0000-0000-000000000003";
const ASSET_ID = "00000000-0000-0000-0000-000000000011";

const portfolios = [
  {
    id: PORTFOLIO_ID,
    name: "Primary portfolio",
    base_currency: "USD",
    benchmark_asset_id: null,
    created_at: "2025-01-02T15:00:00Z",
    updated_at: "2026-09-15T22:00:00Z",
  },
  {
    id: SECOND_PORTFOLIO_ID,
    name: "Income portfolio",
    base_currency: "USD",
    benchmark_asset_id: null,
    created_at: "2025-02-02T15:00:00Z",
    updated_at: "2026-09-15T22:00:00Z",
  },
];

const asset = {
  id: ASSET_ID,
  symbol: "AAPL",
  name: "Apple Inc.",
  asset_type: "STOCK",
  exchange: "NASDAQ",
  currency: "USD",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function createQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0 },
      mutations: { retry: false },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
      email: "owner@example.com",
      first_name: "Portfolio",
      last_name: "Owner",
    },
  });

  return queryClient;
}

function renderPage(initialEntry = `/activity?portfolio=${PORTFOLIO_ID}`) {
  const queryClient = createQueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/activity" element={<ActivityPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

function baseFetch(
  handler?: (url: string, init?: RequestInit) => Promise<Response> | Response | null,
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const handled = await handler?.(url, init);
    if (handled) {
      return handled;
    }

    if (url.endsWith("/api/v1/portfolios/")) {
      return jsonResponse(portfolios);
    }

    if (url.endsWith("/api/v1/assets/")) {
      return jsonResponse([asset]);
    }

    if (
      url.includes("/api/v1/portfolios/") &&
      url.endsWith("/transactions/") &&
      init?.method === "GET"
    ) {
      return jsonResponse([]);
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function selectCsvFile(fileContents = "csv") {
  const file = new File([fileContents], "transactions.csv", { type: "text/csv" });
  Object.defineProperty(file, "text", {
    value: vi.fn(async () => fileContents),
  });

  fireEvent.change(await screen.findByLabelText("CSV file"), {
    target: { files: [file] },
  });

  expect(
    await screen.findByText("Selected: transactions.csv"),
  ).toBeInTheDocument();

  const previewButton = screen.getByRole("button", {
    name: "Validate and preview",
  });

  await waitFor(() => {
    expect(previewButton).toBeEnabled();
  });

  return previewButton;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ActivityPage", () => {
  it("selects an owned portfolio by canonical UUID context", async () => {
    baseFetch();
    renderPage();

    const portfolioSelect = await screen.findByLabelText("Activity portfolio");

    expect(
      screen.getByRole("heading", { name: "Activity & Transactions" }),
    ).toBeInTheDocument();
    expect(portfolioSelect).toHaveValue(PORTFOLIO_ID);
    expect(screen.getByText(PORTFOLIO_ID)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Cash amount"), {
      target: { value: "123.45" },
    });
    expect(screen.getByLabelText("Cash amount")).toHaveValue(123.45);

    fireEvent.change(screen.getByLabelText("Activity portfolio"), {
      target: { value: SECOND_PORTFOLIO_ID },
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Activity portfolio")).toHaveValue(
        SECOND_PORTFOLIO_ID,
      );
    });
    expect(screen.getByText(SECOND_PORTFOLIO_ID)).toBeInTheDocument();
    expect(screen.getByLabelText("Cash amount")).toHaveValue(null);
  });

  it("renders the complete persisted transaction history for the selected portfolio", async () => {
    const depositId = "00000000-0000-0000-0000-000000000050";
    const buyId = "00000000-0000-0000-0000-000000000051";

    baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/transactions/`) &&
        init?.method === "GET"
      ) {
        return jsonResponse([
          {
            id: buyId,
            portfolio_id: PORTFOLIO_ID,
            transaction_type: "BUY",
            asset_id: ASSET_ID,
            asset_symbol: "AAPL",
            occurred_at: "2026-09-16T15:00:00Z",
            source_sequence: 0,
            quantity: "2.000000000000",
            price: "100.00000000",
            fees: "1.00000000",
            cash_amount: null,
            created_at: "2026-09-16T15:00:01Z",
          },
          {
            id: depositId,
            portfolio_id: PORTFOLIO_ID,
            transaction_type: "DEPOSIT",
            asset_id: null,
            asset_symbol: null,
            occurred_at: "2026-09-15T14:00:00Z",
            source_sequence: 0,
            quantity: null,
            price: null,
            fees: "0.00000000",
            cash_amount: "2500.00000000",
            created_at: "2026-09-15T14:00:01Z",
          },
        ]);
      }
      return null;
    });

    renderPage();

    const table = await screen.findByRole("table", {
      name: "Complete transaction history for the selected portfolio",
    });
    expect(within(table).getByText("Buy")).toBeInTheDocument();
    expect(within(table).getByText("Deposit")).toBeInTheDocument();
    expect(within(table).getByText("AAPL")).toBeInTheDocument();
    expect(within(table).getByText("2,500")).toBeInTheDocument();
    expect(within(table).getByText(depositId)).toBeInTheDocument();
    expect(
      screen.getByLabelText("2 transactions"),
    ).toBeInTheDocument();
  });

  it("submits manual activity to the selected owner-scoped transaction API and surfaces server validation", async () => {
    document.cookie = "csrftoken=activity-manual; path=/";
    const fetchMock = baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/transactions/`) &&
        init?.method === "POST"
      ) {
        return jsonResponse(
          {
            code: "INVALID_TRANSACTION",
            errors: { cash_amount: ["cash_amount must be greater than zero."] },
          },
          400,
        );
      }
      return null;
    });

    renderPage();

    fireEvent.change(await screen.findByLabelText("Cash amount"), {
      target: { value: "0" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record transaction" }));

    expect(
      await screen.findByText("cash_amount must be greater than zero."),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/transactions/`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders CSV preview rows and blocks atomic confirmation while any row is invalid", async () => {
    document.cookie = "csrftoken=activity-preview; path=/";
    baseFetch((url, init) => {
      if (
        url.endsWith(
          `/api/v1/portfolios/${PORTFOLIO_ID}/transactions/import/preview/`,
        ) &&
        init?.method === "POST"
      ) {
        return jsonResponse({
          row_count: 2,
          valid_count: 1,
          invalid_count: 1,
          can_import: false,
          atomic: true,
          rows: [
            {
              row_number: 2,
              valid: true,
              transaction_type: "DEPOSIT",
              occurred_at: "2026-09-15T13:00:00+00:00",
              asset_id: null,
              asset_symbol: null,
              quantity: null,
              price: null,
              fees: "0",
              cash_amount: "1000.00",
              issues: [],
            },
            {
              row_number: 3,
              valid: false,
              transaction_type: "BUY",
              occurred_at: "2026-09-15T14:00:00+00:00",
              asset_id: ASSET_ID,
              asset_symbol: null,
              quantity: "1",
              price: "100",
              fees: "0",
              cash_amount: null,
              issues: [
                {
                  code: "ASSET_NOT_FOUND",
                  field: "asset_id",
                  message: "Canonical asset was not found or is inactive.",
                },
              ],
            },
          ],
        });
      }
      return null;
    });

    renderPage();
    fireEvent.click(await selectCsvFile());

    expect(await screen.findByText("2 rows")).toBeInTheDocument();
    expect(screen.getByText("1 valid")).toBeInTheDocument();
    expect(screen.getByText("1 invalid")).toBeInTheDocument();
    expect(screen.getByText(/ASSET_NOT_FOUND:/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirm atomic import" }),
    ).toBeDisabled();
  });

  it("requires explicit CSV confirmation and invalidates authoritative derived reads after commit", async () => {
    document.cookie = "csrftoken=activity-confirm; path=/";
    let confirmCalls = 0;
    baseFetch((url, init) => {
      if (url.endsWith("/import/preview/") && init?.method === "POST") {
        return jsonResponse({
          row_count: 1,
          valid_count: 1,
          invalid_count: 0,
          can_import: true,
          atomic: true,
          rows: [
            {
              row_number: 2,
              valid: true,
              transaction_type: "DEPOSIT",
              occurred_at: "2026-09-15T13:00:00+00:00",
              asset_id: null,
              asset_symbol: null,
              quantity: null,
              price: null,
              fees: "0",
              cash_amount: "1000.00",
              issues: [],
            },
          ],
        });
      }

      if (url.endsWith("/import/confirm/") && init?.method === "POST") {
        confirmCalls += 1;
        return jsonResponse({ imported_count: 1, transactions: [] }, 201);
      }

      return null;
    });

    const queryClient = renderPage();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    fireEvent.click(await selectCsvFile());
    const confirm = await screen.findByRole("button", {
      name: "Confirm atomic import",
    });

    expect(confirmCalls).toBe(0);
    fireEvent.click(confirm);

    expect(
      await screen.findByText(/1 transaction imported atomically/),
    ).toBeInTheDocument();
    expect(confirmCalls).toBe(1);
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-transactions", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-dashboard", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-analysis", PORTFOLIO_ID],
    });
  });

  it("keeps confirmation atomic when server revalidation fails", async () => {
    document.cookie = "csrftoken=activity-revalidation; path=/";
    baseFetch((url, init) => {
      const preview = {
        row_count: 1,
        valid_count: 1,
        invalid_count: 0,
        can_import: true,
        atomic: true,
        rows: [
          {
            row_number: 2,
            valid: true,
            transaction_type: "DEPOSIT",
            occurred_at: "2026-09-15T13:00:00+00:00",
            asset_id: null,
            asset_symbol: null,
            quantity: null,
            price: null,
            fees: "0",
            cash_amount: "1000.00",
            issues: [],
          },
        ],
      };

      if (url.endsWith("/import/preview/") && init?.method === "POST") {
        return jsonResponse(preview);
      }

      if (url.endsWith("/import/confirm/") && init?.method === "POST") {
        return jsonResponse(
          {
            code: "IMPORT_VALIDATION_FAILED",
            detail: "CSV import contains invalid rows and was not committed.",
            preview: {
              ...preview,
              valid_count: 0,
              invalid_count: 1,
              can_import: false,
              rows: [
                {
                  ...preview.rows[0],
                  valid: false,
                  issues: [
                    {
                      code: "ORDERING_CONFLICT",
                      field: "non_field_errors",
                      message: "Ledger changed after preview.",
                    },
                  ],
                },
              ],
            },
          },
          400,
        );
      }

      return null;
    });

    renderPage();

    fireEvent.click(await selectCsvFile());
    fireEvent.click(
      await screen.findByRole("button", { name: "Confirm atomic import" }),
    );

    expect(
      await screen.findByText(/Import was not committed:/),
    ).toBeInTheDocument();
    const table = screen.getByRole("table", {
      name: "Transaction CSV validation preview",
    });
    expect(within(table).getByText(/ORDERING_CONFLICT:/)).toBeInTheDocument();
  });

  it("states unsupported history mutation capabilities instead of rendering fake controls", async () => {
    baseFetch();
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Current transaction capabilities",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/editing, deletion, and reconciliation are not exposed/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /delete transaction/i }),
    ).not.toBeInTheDocument();
  });
});
