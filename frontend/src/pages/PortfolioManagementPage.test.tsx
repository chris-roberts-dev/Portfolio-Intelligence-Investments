import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { PortfolioManagementPage } from "./PortfolioManagementPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_ID = "00000000-0000-0000-0000-000000000011";

const portfolio = {
  id: PORTFOLIO_ID,
  name: "Primary portfolio",
  base_currency: "USD",
  benchmark_asset_id: null,
  created_at: "2025-01-02T15:00:00Z",
  updated_at: "2026-09-15T22:00:00Z",
};

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

function renderPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter
        initialEntries={[
          `/portfolios/${PORTFOLIO_ID}/manage?range=6M`,
        ]}
      >
        <Routes>
          <Route
            path="/portfolios/:portfolioId/manage"
            element={<PortfolioManagementPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
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
      return jsonResponse([portfolio]);
    }

    if (url.endsWith("/api/v1/assets/")) {
      return jsonResponse([asset]);
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

describe("PortfolioManagementPage", () => {
  it("preserves dashboard range context and renames through the owner-scoped API", async () => {
    document.cookie = "csrftoken=rename-page; path=/";
    let renamed = false;
    const fetchMock = baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/`) &&
        init?.method === "PATCH"
      ) {
        renamed = true;
        return jsonResponse({ ...portfolio, name: "Renamed portfolio" });
      }

      if (url.endsWith("/api/v1/portfolios/") && renamed) {
        return jsonResponse([{ ...portfolio, name: "Renamed portfolio" }]);
      }

      return null;
    });

    renderPage();

    expect(
      await screen.findByRole("link", { name: "Portfolio dashboard" }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );

    const nameInput = await screen.findByLabelText("Portfolio name");
    fireEvent.change(nameInput, { target: { value: "Renamed portfolio" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByText("Portfolio name saved.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Renamed portfolio" }),
      }),
    );
  });


  it("selects and clears a canonical benchmark through the owner-scoped API", async () => {
    document.cookie = "csrftoken=benchmark-page; path=/";
    const benchmark = {
      id: "00000000-0000-0000-0000-000000000099",
      symbol: "SPY",
      name: "SPDR S&P 500 ETF Trust",
      asset_type: "ETF",
      exchange: "NYSEARCA",
      currency: "USD",
    };
    let benchmarkAssetId: string | null = null;

    const fetchMock = baseFetch((url, init) => {
      if (url.endsWith("/api/v1/assets/")) {
        return jsonResponse([asset, benchmark]);
      }

      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/benchmark/`) &&
        init?.method === "PATCH"
      ) {
        const body = JSON.parse(String(init.body)) as {
          benchmark_asset_id: string | null;
        };
        benchmarkAssetId = body.benchmark_asset_id;
        return jsonResponse({
          ...portfolio,
          benchmark_asset_id: benchmarkAssetId,
        });
      }

      if (url.endsWith("/api/v1/portfolios/") && benchmarkAssetId !== null) {
        return jsonResponse([
          { ...portfolio, benchmark_asset_id: benchmarkAssetId },
        ]);
      }

      return null;
    });

    renderPage();

    const benchmarkSelect = await screen.findByLabelText("Benchmark asset");
    fireEvent.change(benchmarkSelect, { target: { value: benchmark.id } });
    fireEvent.click(screen.getByRole("button", { name: "Save benchmark" }));

    expect(
      await screen.findByText("Benchmark selection saved."),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/benchmark/`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ benchmark_asset_id: benchmark.id }),
      }),
    );

    fireEvent.change(benchmarkSelect, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Save benchmark" }));

    expect(await screen.findByText("Benchmark cleared.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/benchmark/`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ benchmark_asset_id: null }),
      }),
    );
  });

  it("shows authoritative manual-transaction field errors without calculating portfolio state", async () => {
    document.cookie = "csrftoken=manual-page; path=/";
    baseFetch((url, init) => {
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
  });

  it("renders valid and invalid CSV preview rows and blocks confirmation when any row is invalid", async () => {
    document.cookie = "csrftoken=csv-preview-page; path=/";
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

    const previewButton = await selectCsvFile();
    fireEvent.click(previewButton);

    expect(await screen.findByText("2 rows")).toBeInTheDocument();
    expect(screen.getByText("1 valid")).toBeInTheDocument();
    expect(screen.getByText("1 invalid")).toBeInTheDocument();
    expect(screen.getByText(/ASSET_NOT_FOUND:/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirm atomic import" }),
    ).toBeDisabled();
  });

  it("requires explicit confirmation and reports successful atomic CSV commit", async () => {
    document.cookie = "csrftoken=csv-confirm-page; path=/";
    let confirmCalls = 0;
    baseFetch((url, init) => {
      if (
        url.endsWith(
          `/api/v1/portfolios/${PORTFOLIO_ID}/transactions/import/preview/`,
        ) &&
        init?.method === "POST"
      ) {
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

      if (
        url.endsWith(
          `/api/v1/portfolios/${PORTFOLIO_ID}/transactions/import/confirm/`,
        ) &&
        init?.method === "POST"
      ) {
        confirmCalls += 1;
        return jsonResponse(
          { imported_count: 1, transactions: [] },
          201,
        );
      }

      return null;
    });

    renderPage();

    const previewButton = await selectCsvFile();
    fireEvent.click(previewButton);

    const confirm = await screen.findByRole("button", {
      name: "Confirm atomic import",
    });
    expect(confirm).toBeEnabled();
    expect(confirmCalls).toBe(0);

    fireEvent.click(confirm);

    expect(
      await screen.findByText(/1 transaction imported atomically/),
    ).toBeInTheDocument();
    expect(confirmCalls).toBe(1);
  });

  it("keeps the import uncommitted and displays confirm-time revalidation failure", async () => {
    document.cookie = "csrftoken=csv-confirm-failure; path=/";
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

    const previewButton = await selectCsvFile();
    fireEvent.click(previewButton);
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
});
