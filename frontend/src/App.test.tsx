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
