import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { App } from "./App";

vi.mock("./components/charts/MarketPriceChart", () => ({
  MarketPriceChart: () => <div>Price chart</div>,
}));

vi.mock("./components/charts/MarketCandlestickChart", () => ({
  MarketCandlestickChart: () => <div>Candlestick chart</div>,
}));

vi.mock("./components/charts/AllocationComparisonChart", () => ({
  AllocationComparisonChart: () => <div>Allocation comparison chart</div>,
}));

vi.mock("./components/charts/EfficientFrontierChart", () => ({
  EfficientFrontierChart: () => <div>Efficient frontier chart</div>,
}));

function renderApp(initialEntry = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        retryDelay: 0,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App authentication routing", () => {
  it("redirects an anonymous protected route to sign in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ authenticated: false, user: null }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    renderApp("/portfolios/portfolio-1/dashboard?range=1M");

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("renders protected portfolio content for an authenticated session", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/v1/auth/session/")) {
        return new Response(
          JSON.stringify({
            authenticated: true,
            user: {
              id: "00000000-0000-0000-0000-000000000001",
              email: "owner@example.com",
              first_name: "Portfolio",
              last_name: "Owner",
            },
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      }

      if (url.endsWith("/api/v1/portfolios/")) {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Select or create a portfolio" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });

  it("routes an authenticated user to the Market Data Explorer", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/v1/auth/session/")) {
          return new Response(
            JSON.stringify({
              authenticated: true,
              user: {
                id: "00000000-0000-0000-0000-000000000001",
                email: "owner@example.com",
                first_name: "Portfolio",
                last_name: "Owner",
              },
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          );
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderApp("/market-data");

    expect(
      await screen.findByRole("heading", {
        name: "Market Data Explorer",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Submit a market-data query"),
    ).toBeInTheDocument();
  });


  it("protects the Allocation Lab route", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ authenticated: false, user: null }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    renderApp(
      "/allocation-lab",
    );

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("routes an authenticated user to the Allocation Lab", async () => {
    const portfolioId = "00000000-0000-0000-0000-000000000002";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/v1/auth/session/")) {
          return new Response(
            JSON.stringify({
              authenticated: true,
              user: {
                id: "00000000-0000-0000-0000-000000000001",
                email: "owner@example.com",
                first_name: "Portfolio",
                last_name: "Owner",
              },
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          );
        }

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(
            JSON.stringify([
              {
                id: portfolioId,
                name: "Primary portfolio",
                base_currency: "USD",
                benchmark_asset_id: null,
                created_at: "2025-01-02T15:00:00Z",
                updated_at: "2026-09-15T22:00:00Z",
              },
            ]),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          );
        }

        if (url.includes(`/api/v1/portfolios/${portfolioId}/dashboard/`)) {
          return new Response(
            JSON.stringify({
              snapshot: {
                snapshot_id: "snapshot-1",
                portfolio_id: portfolioId,
                base_currency: "USD",
                provider: "mock",
                requested_start: "2026-03-17",
                requested_end_exclusive: "2026-09-18",
                effective_start: "2026-03-17",
                effective_end_exclusive: "2026-09-18",
                valuation_cutoff: "2026-09-17T16:00:00Z",
                calculated_at: "2026-09-17T16:00:00Z",
                engine_version: "0.1.0",
                current_data_as_of: null,
                historical_data_as_of: null,
                analytics_as_of_date: null,
              },
              is_complete: true,
              modules: [],
              summary: null,
              performance: null,
              allocation: null,
              holdings: {
                holdings: [],
                data_quality: "CURRENT",
                warnings: [],
                provenance: {
                  portfolio_id: portfolioId,
                  base_currency: "USD",
                  provider: "mock",
                  requested_start: "2026-03-17",
                  requested_end_exclusive: "2026-09-18",
                  effective_start: "2026-03-17",
                  effective_end_exclusive: "2026-09-18",
                  current_price_as_of: null,
                  period_data_as_of: null,
                  calculated_at: "2026-09-17T16:00:00Z",
                  current_price_field: "adjusted_close",
                  period_price_field: "adjusted_close",
                },
              },
              movers: null,
              analytics: null,
              review_items: null,
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          );
        }

        if (url.endsWith("/api/v1/assets/")) {
          return new Response(JSON.stringify([]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        if (url.endsWith("/api/v1/optimization-runs/")) {
          return new Response(JSON.stringify([]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderApp("/allocation-lab");

    expect(
      await screen.findByRole("heading", { name: "Allocation Lab" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("No assets selected")).toBeInTheDocument();
  });

  it("routes an authenticated user to portfolio management with preserved context", async () => {
    const portfolioId = "00000000-0000-0000-0000-000000000002";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/v1/auth/session/")) {
          return new Response(
            JSON.stringify({
              authenticated: true,
              user: {
                id: "00000000-0000-0000-0000-000000000001",
                email: "owner@example.com",
                first_name: "Portfolio",
                last_name: "Owner",
              },
            }),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          );
        }

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(
            JSON.stringify([
              {
                id: portfolioId,
                name: "Primary portfolio",
                base_currency: "USD",
                benchmark_asset_id: null,
                created_at: "2025-01-02T15:00:00Z",
                updated_at: "2026-09-15T22:00:00Z",
              },
            ]),
            {
              status: 200,
              headers: { "content-type": "application/json" },
            },
          );
        }

        if (url.endsWith("/api/v1/assets/")) {
          return new Response(JSON.stringify([]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderApp(`/portfolios/${portfolioId}/manage?range=6M`);

    expect(
      await screen.findByRole("heading", { name: "Add transaction" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Portfolio dashboard" }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${portfolioId}/dashboard?range=6M`,
    );
  });
});