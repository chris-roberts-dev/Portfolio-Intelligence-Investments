import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { HoldingDetailPage } from "./HoldingDetailPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_ID = "00000000-0000-0000-0000-000000000012";
const OTHER_ASSET_ID = "00000000-0000-0000-0000-000000000099";

vi.mock("../components/charts/MarketPriceChart", () => ({
  MarketPriceChart: ({ results }: { results: Array<{ symbol: string }> }) => (
    <div data-testid="market-price-chart">{results[0]?.symbol} price chart</div>
  ),
}));

vi.mock("../components/charts/MarketCandlestickChart", () => ({
  MarketCandlestickChart: ({ result }: { result: { symbol: string } }) => (
    <div data-testid="market-candlestick-chart">{result.symbol} candlestick chart</div>
  ),
}));

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
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

function portfolioListResponse() {
  return [
    {
      id: PORTFOLIO_ID,
      name: "Historical portfolio",
      base_currency: "USD",
      benchmark_asset_id: null,
      ledger_inception_at: "2020-01-02T14:00:00Z",
      created_at: "2026-09-18T12:00:00Z",
      updated_at: "2026-09-18T12:00:00Z",
    },
  ];
}

function dashboardResponse() {
  return {
    snapshot: {
      snapshot_id: "snapshot-1",
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-06-18",
      requested_end_exclusive: "2026-09-19",
      effective_start: "2026-06-18",
      effective_end_exclusive: "2026-09-19",
      valuation_cutoff: "2026-09-18T21:00:00Z",
      calculated_at: "2026-09-18T21:05:00Z",
      engine_version: "test",
      current_data_as_of: "2026-09-18T20:00:00Z",
      historical_data_as_of: "2026-09-18T20:00:00Z",
      analytics_as_of_date: "2026-09-18",
    },
    is_complete: true,
    modules: [
      {
        module: "HOLDINGS",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
    ],
    summary: null,
    performance: null,
    allocation: null,
    holdings: {
      holdings: [
        {
          asset_id: ASSET_ID,
          symbol: "BBB",
          name: "BBB Incorporated",
          asset_type: "STOCK",
          currency: "USD",
          quantity: "10.000000000000",
          current_price: "105.00",
          current_price_date: "2026-09-18",
          current_price_retrieved_at: "2026-09-18T20:00:00Z",
          stale_trading_sessions: 0,
          market_value: "1050.00",
          weight: 0.42,
          weight_unavailable_reason: null,
          selected_period_return: 0.08,
          selected_period_return_unavailable_reason: null,
          contribution_to_return: 0.031,
          contribution_unavailable_reason: null,
          sparkline: [],
          data_quality: "CURRENT",
          warnings: [],
        },
      ],
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id: PORTFOLIO_ID,
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-06-18",
        requested_end_exclusive: "2026-09-19",
        effective_start: "2026-06-18",
        effective_end_exclusive: "2026-09-19",
        current_price_as_of: "2026-09-18T20:00:00Z",
        period_data_as_of: "2026-09-18T20:00:00Z",
        calculated_at: "2026-09-18T21:05:00Z",
        current_price_field: "close",
        period_price_field: "adjusted_close",
      },
    },
    movers: null,
    analytics: null,
    review_items: null,
  };
}

function marketResponse(assetId: string) {
  return {
    results: [
      {
        symbol: "BBB",
        asset_id: assetId,
        status: "SUCCEEDED",
        bars: [
          {
            asset_id: assetId,
            trade_date: "2026-09-18",
            open: 103,
            high: 106,
            low: 102,
            close: 105,
            adjusted_close: 105,
            volume: 1000000,
            source: "mock",
            retrieved_at: "2026-09-18T20:00:00Z",
          },
        ],
        warnings: [],
      },
    ],
    meta: {
      provider: "mock",
      retrieved_at: "2026-09-18T20:00:00Z",
      interval: "1d",
      start: "2026-06-18",
      end: "2026-09-19",
    },
    row_count: 1,
  };
}

function installFetch(marketAssetId = ASSET_ID) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url === "/api/v1/portfolios/") {
      return new Response(JSON.stringify(portfolioListResponse()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (url.startsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
      return new Response(JSON.stringify(dashboardResponse()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (url === "/api/v1/market-data/bars/query/") {
      const body = JSON.parse(String(init?.body)) as {
        symbols: string[];
        start: string;
        end: string;
        interval: string;
      };

      expect(body).toEqual({
        symbols: ["BBB"],
        start: "2026-06-18",
        end: "2026-09-19",
        interval: "1d",
      });

      return new Response(JSON.stringify(marketResponse(marketAssetId)), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPage() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter
        initialEntries={[
          `/portfolios/${PORTFOLIO_ID}/holdings/${ASSET_ID}?range=3M&view=holdings`,
        ]}
      >
        <Routes>
          <Route
            path="/portfolios/:portfolioId/holdings/:assetId"
            element={<HoldingDetailPage />}
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

describe("HoldingDetailPage", () => {
  it("reloads from canonical asset identity, preserves portfolio context, and researches the same reporting period", async () => {
    installFetch();
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "BBB" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "BBB · BBB Incorporated" }),
    ).toBeInTheDocument();
    expect(screen.getByText(ASSET_ID)).toBeInTheDocument();
    expect(screen.getByText("+8.00%")).toBeInTheDocument();

    expect(await screen.findByTestId("market-price-chart")).toHaveTextContent(
      "BBB price chart",
    );
    expect(await screen.findByTestId("market-candlestick-chart")).toHaveTextContent(
      "BBB candlestick chart",
    );

    expect(
      screen.getByRole("link", { name: "Back to portfolio" }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=3M&view=holdings`,
    );

    const marketExplorer = screen.getByRole("link", {
      name: "Open in Market Data Explorer",
    });
    const href = marketExplorer.getAttribute("href") ?? "";
    expect(href).toContain("/market-data?");
    expect(href).toContain("symbol=BBB");
    expect(href).toContain(`asset=${ASSET_ID}`);
    expect(href).toContain(`portfolio=${PORTFOLIO_ID}`);
    expect(href).toContain("range=3M");
    expect(href).toContain("view=holdings");
  });

  it("withholds research charts when ticker resolution does not match the canonical route asset", async () => {
    installFetch(OTHER_ASSET_ID);
    renderPage();

    expect(
      await screen.findByText("Canonical asset identity mismatch"),
    ).toBeInTheDocument();
    expect(screen.getByText(OTHER_ASSET_ID, { exact: false })).toBeInTheDocument();
    expect(screen.queryByTestId("market-price-chart")).not.toBeInTheDocument();
    expect(screen.queryByTestId("market-candlestick-chart")).not.toBeInTheDocument();
  });
});
