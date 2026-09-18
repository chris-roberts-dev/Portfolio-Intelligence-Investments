import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { DashboardPage } from "./DashboardPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
    },
  });

  return queryClient;
}

function portfolioPayload() {
  return [
    {
      id: PORTFOLIO_ID,
      name: "Historical portfolio",
      base_currency: "USD",
      benchmark_asset_id: null,
      ledger_inception_at: "2020-01-02T14:00:00Z",
      created_at: "2026-09-18T13:00:00Z",
      updated_at: "2026-09-18T14:00:00Z",
    },
  ];
}

function renderPage(initialEntry: string) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/portfolios/:portfolioId/dashboard"
            element={<DashboardPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("DashboardPage portfolio report", () => {
  it("uses ledger inception rather than portfolio creation for Since Inception", async () => {
    const requestedUrls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        requestedUrls.push(url);

        if (url.endsWith("/api/v1/portfolios/")) {
          return Promise.resolve(
            new Response(JSON.stringify(portfolioPayload()), {
              status: 200,
              headers: { "content-type": "application/json" },
            }),
          );
        }

        if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
          return new Promise<Response>(() => undefined);
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage(`/portfolios/${PORTFOLIO_ID}/dashboard?range=ALL`);

    expect(
      await screen.findByRole("heading", { name: "Historical portfolio" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Inception: Jan 2, 2020/)).toBeInTheDocument();

    await waitFor(() => {
      expect(
        requestedUrls.some(
          (url) =>
            url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`) &&
            url.includes("start=2020-01-02"),
        ),
      ).toBe(true);
    });
  });

  it("uses URL-addressable report subviews while preserving portfolio UUID and range", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/portfolios/")) {
          return Promise.resolve(
            new Response(JSON.stringify(portfolioPayload()), {
              status: 200,
              headers: { "content-type": "application/json" },
            }),
          );
        }
        if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
          return new Promise<Response>(() => undefined);
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=holdings`,
    );

    const navigation = await screen.findByRole("navigation", {
      name: "Portfolio report sections",
    });
    const holdings = screen.getByRole("link", { name: "Holdings" });
    expect(holdings).toHaveAttribute("aria-current", "page");
    expect(holdings).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=holdings`,
    );
    expect(screen.getByRole("link", { name: "Allocation" })).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=allocation`,
    );
    expect(screen.getByRole("link", { name: "Performance" })).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=performance`,
    );
    expect(screen.getByRole("link", { name: "Risk" })).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=risk`,
    );
    expect(screen.getByRole("link", { name: "Transactions" })).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=transactions`,
    );
    expect(navigation).toContainElement(holdings);

    expect(screen.getByRole("link", { name: "Add transaction" })).toHaveAttribute(
      "href",
      `/activity?portfolio=${PORTFOLIO_ID}`,
    );
  });

  it("renders the Transactions subview from the ledger without requiring a market-data dashboard snapshot", async () => {
    const requestedUrls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        requestedUrls.push(url);

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify(portfolioPayload()), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        if (url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/transactions/`)) {
          return new Response(
            JSON.stringify([
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
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=transactions`,
    );

    expect(
      await screen.findByRole("heading", { name: "Transactions" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Transaction history" }),
    ).toBeInTheDocument();
    expect(screen.getByText("10,000")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open Activity & Transactions" }),
    ).toHaveAttribute("href", `/activity?portfolio=${PORTFOLIO_ID}`);

    expect(
      requestedUrls.some((url) => url.includes(`/dashboard/`)),
    ).toBe(false);
  });

  it("preserves the active detail view when the reporting period changes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/portfolios/")) {
          return Promise.resolve(
            new Response(JSON.stringify(portfolioPayload()), {
              status: 200,
              headers: { "content-type": "application/json" },
            }),
          );
        }
        if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
          return new Promise<Response>(() => undefined);
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=YTD&view=risk`,
    );

    const rangeControls = await screen.findByRole("group", {
      name: "Portfolio report date range",
    });
    fireEvent.click(
      screen.getByRole("button", { name: "5Y" }),
    );

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Risk" })).toHaveAttribute(
        "href",
        `/portfolios/${PORTFOLIO_ID}/dashboard?range=5Y&view=risk`,
      );
    });
    expect(rangeControls).toBeInTheDocument();
  });

  it("invokes the browser print flow for Print / Export PDF from detail views", async () => {
    const printMock = vi.fn();
    Object.defineProperty(window, "print", {
      configurable: true,
      value: printMock,
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/portfolios/")) {
          return Promise.resolve(
            new Response(JSON.stringify(portfolioPayload()), {
              status: 200,
              headers: { "content-type": "application/json" },
            }),
          );
        }
        if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
          return new Promise<Response>(() => undefined);
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=YTD&view=risk`,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Print / Export PDF" }),
    );
    expect(printMock).toHaveBeenCalledTimes(1);
  });
});
