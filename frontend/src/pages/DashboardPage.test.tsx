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

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter
          initialEntries={[`/portfolios/${PORTFOLIO_ID}/dashboard?range=ALL`]}
        >
          <Routes>
            <Route
              path="/portfolios/:portfolioId/dashboard"
              element={<DashboardPage />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

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

  it("renders report navigation and preserves portfolio context for transaction work", async () => {
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

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={[`/portfolios/${PORTFOLIO_ID}/dashboard?range=YTD`]}>
          <Routes>
            <Route path="/portfolios/:portfolioId/dashboard" element={<DashboardPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("navigation", { name: "Portfolio report sections" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Transactions" })).toHaveAttribute(
      "href",
      `/activity?portfolio=${PORTFOLIO_ID}`,
    );
    expect(screen.getByRole("link", { name: "Add transaction" })).toHaveAttribute(
      "href",
      `/activity?portfolio=${PORTFOLIO_ID}`,
    );
  });

  it("invokes the browser print flow for Print / Export PDF", async () => {
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

    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={[`/portfolios/${PORTFOLIO_ID}/dashboard?range=YTD`]}>
          <Routes>
            <Route path="/portfolios/:portfolioId/dashboard" element={<DashboardPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Print / Export PDF" }),
    );
    expect(printMock).toHaveBeenCalledTimes(1);
  });
});
