import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { HomePage } from "./HomePage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

vi.mock("../components/charts/PerformanceChart", () => ({
  PerformanceChart: () => <div data-testid="overview-performance-chart">Performance chart</div>,
}));

vi.mock("../components/overview/OverviewAllocationChart", () => ({
  OverviewAllocationChart: () => <div data-testid="overview-allocation-chart">Allocation chart</div>,
}));

function createQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0 },
      mutations: { retry: false },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "owner@example.com",
      first_name: "Portfolio",
      last_name: "Owner",
    },
  });

  return queryClient;
}

function portfolio() {
  return {
    id: PORTFOLIO_ID,
    name: "Primary portfolio",
    base_currency: "USD",
    benchmark_asset_id: "00000000-0000-0000-0000-000000000099",
    created_at: "2025-01-02T15:00:00Z",
    updated_at: "2026-09-15T22:00:00Z",
  };
}

function dashboardSnapshot() {
  return {
    snapshot: {
      snapshot_id: "snapshot-1",
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-01-01",
      requested_end_exclusive: "2026-09-18",
      effective_start: "2026-01-01",
      effective_end_exclusive: "2026-09-18",
      valuation_cutoff: "2026-09-17T16:00:00Z",
      calculated_at: "2026-09-17T16:05:00Z",
      engine_version: "0.1.0",
      current_data_as_of: "2026-09-17T16:00:00Z",
      historical_data_as_of: "2026-09-17T16:00:00Z",
      analytics_as_of_date: "2026-09-17",
    },
    is_complete: true,
    modules: [],
    summary: {
      metrics: {
        total_market_value: "125000.00",
        total_market_value_unavailable_reason: null,
        net_contributions: "100000.00",
        cost_basis: "100000.00",
        cash_balance: "5000.00",
        cash_percentage: "0.04",
        cash_percentage_unavailable_reason: null,
        unrealized_gain_loss: "22000.00",
        unrealized_gain_loss_unavailable_reason: null,
        selected_period_realized_gain_loss: "3000.00",
        selected_period_realized_gain_loss_unavailable_reason: null,
        selected_period_income_received: "400.00",
        selected_period_income_unavailable_reason: null,
      },
      data_quality: "CURRENT",
      warnings: [],
      provenance: {},
    },
    performance: {
      summary: {
        starting_value: "100000.00",
        ending_value: "125000.00",
        value_change: "25000.00",
        net_external_flow: "10000.00",
        investment_gain_loss: "15000.00",
        cumulative_return: 0.128,
        benchmark_cumulative_return: 0.104,
      },
      points: [],
      benchmark_points: [],
      portfolio_data_quality: "CURRENT",
      benchmark_data_quality: "CURRENT",
      warnings: [],
      provenance: {
        benchmark_symbol: "SPY",
      },
    },
    allocation: {
      allocation_available: true,
      groups: [
        {
          key: "stock",
          label: "Stocks",
          is_cash: false,
          asset_count: 3,
          market_value: "120000.00",
          weight: 0.96,
        },
        {
          key: "cash",
          label: "Cash",
          is_cash: true,
          asset_count: 0,
          market_value: "5000.00",
          weight: 0.04,
        },
      ],
      totals: {
        total_market_value: "125000.00",
        invested_value: "120000.00",
        cash_value: "5000.00",
        invested_weight: 0.96,
        cash_weight: 0.04,
      },
      data_quality: "CURRENT",
      unavailable_reason: null,
      warnings: [],
      provenance: {},
    },
    holdings: null,
    movers: {
      top_gainers: [],
      top_losers: [],
      largest_contributors: [
        {
          asset_id: "00000000-0000-0000-0000-000000000011",
          symbol: "AAPL",
          name: "Apple Inc.",
          asset_type: "STOCK",
          currency: "USD",
          is_current_holding: true,
          quantity: "100",
          current_price: "220.00",
          current_price_date: "2026-09-17",
          current_price_retrieved_at: "2026-09-17T16:00:00Z",
          stale_trading_sessions: 0,
          market_value: "22000.00",
          weight: 0.176,
          selected_period_return: 0.18,
          contribution_to_return: 0.031,
          sparkline: [],
          data_quality: "CURRENT",
          unavailable_reasons: [],
        },
      ],
      largest_detractors: [
        {
          asset_id: "00000000-0000-0000-0000-000000000012",
          symbol: "TSLA",
          name: "Tesla Inc.",
          asset_type: "STOCK",
          currency: "USD",
          is_current_holding: true,
          quantity: "20",
          current_price: "250.00",
          current_price_date: "2026-09-17",
          current_price_retrieved_at: "2026-09-17T16:00:00Z",
          stale_trading_sessions: 0,
          market_value: "5000.00",
          weight: 0.04,
          selected_period_return: -0.08,
          contribution_to_return: -0.004,
          sparkline: [],
          data_quality: "CURRENT",
          unavailable_reasons: [],
        },
      ],
      reconciliation: {},
      data_quality: "CURRENT",
      warnings: [],
      provenance: {},
    },
    analytics: {
      portfolio_id: PORTFOLIO_ID,
      observations: 180,
      benchmark_observations: 180,
      cumulative_return: 0.128,
      cagr: null,
      annualized_volatility: 0.117,
      sharpe: null,
      sortino: null,
      maximum_drawdown: {
        value: -0.083,
        observations: 180,
        peak_index: 10,
        trough_index: 30,
        warnings: [],
      },
      beta: null,
      benchmark_correlation: null,
      current_allocation: null,
      concentration: {
        largest_position_weight: 0.34,
        herfindahl_hirschman_index: 0.2,
        security_position_count: 3,
        cash_weight: 0.04,
        largest_position_includes_cash: false,
        hhi_includes_cash: false,
        long_only: true,
        weight_sum_tolerance: 0.000001,
      },
      rolling_return_window: null,
      rolling_returns: [],
      provenance: {},
      warnings: [],
    },
    review_items: {
      counts: {
        total: 1,
        by_severity: [{ key: "WARNING", count: 1 }],
        by_category: [{ key: "MARKET_DATA", count: 1 }],
      },
      filtered_count: 1,
      filters: { severity: null, category: null },
      items: [
        {
          key: "warning-1",
          source: "CURRENT_VALUATION",
          severity: "WARNING",
          category: "MARKET_DATA",
          code: "STALE_PRICE",
          message: "One holding uses a delayed market observation.",
          drilldown: {},
        },
      ],
      provenance: {},
    },
  };
}

function renderHome(initialEntry = "/") {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/portfolios" element={<h1>Portfolios workspace</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HomePage overview", () => {
  it("renders the redesigned server-authoritative overview without portfolio creation controls", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify([portfolio()]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
          return new Response(JSON.stringify(dashboardSnapshot()), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderHome();

    expect(
      await screen.findByRole("heading", { name: "Your Portfolio" }),
    ).toBeInTheDocument();
    expect(screen.getByText("$125,000.00")).toBeInTheDocument();
    expect(screen.getByText("YTD Return")).toBeInTheDocument();
    expect(screen.getByText("Since Inception")).toBeInTheDocument();
    expect(screen.getByText("Risk Level")).toBeInTheDocument();
    expect(screen.getByTestId("overview-performance-chart")).toBeInTheDocument();
    expect(screen.getByTestId("overview-allocation-chart")).toBeInTheDocument();
    expect(screen.queryByLabelText("Portfolio name")).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Manage portfolios" }),
    ).toHaveAttribute("href", "/portfolios");
  });

  it("exposes All Portfolios honestly without calculating consolidated analytics in React", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify([portfolio()]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
          return new Response(JSON.stringify(dashboardSnapshot()), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderHome();

    const selector = await screen.findByLabelText("Overview portfolio");
    fireEvent.change(selector, { target: { value: "all" } });

    expect(
      await screen.findByText("Consolidated overview is not available yet"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("overview-performance-chart")).not.toBeInTheDocument();
  });

  it("uses the focused onboarding state when the authenticated user has no portfolios", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify([]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderHome();

    expect(
      await screen.findByText("Select or create a portfolio"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create portfolio" })).toHaveAttribute(
      "href",
      "/portfolios",
    );
  });
});
