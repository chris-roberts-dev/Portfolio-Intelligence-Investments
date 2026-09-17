import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import type { OptimizationRun } from "../types/optimization";
import { AllocationLabPage } from "./AllocationLabPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const AAPL_ID = "00000000-0000-0000-0000-000000000011";
const MSFT_ID = "00000000-0000-0000-0000-000000000012";

vi.mock("../components/charts/AllocationComparisonChart", () => ({
  AllocationComparisonChart: ({
    baselineLabel,
  }: {
    baselineLabel?: string;
  }) => (
    <div data-testid="allocation-comparison-chart">
      {baselineLabel ?? "Current observed"}
    </div>
  ),
}));

vi.mock("../components/charts/EfficientFrontierChart", () => ({
  EfficientFrontierChart: () => (
    <div data-testid="efficient-frontier-chart">Efficient frontier chart</div>
  ),
}));

function queryClient(): QueryClient {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0 },
      mutations: { retry: false },
    },
  });

  client.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "owner@example.com",
      first_name: "Portfolio",
      last_name: "Owner",
    },
  });
  return client;
}

function asset(id: string, symbol: string, name: string) {
  return {
    id,
    symbol,
    name,
    asset_type: "STOCK",
    exchange: "NASDAQ",
    currency: "USD",
  };
}

function run(
  overrides: Partial<OptimizationRun> = {},
): OptimizationRun {
  return {
    id: "run-1",
    source_type: "AD_HOC",
    portfolio_id: null,
    portfolio_name: null,
    status: "SUCCEEDED",
    method: "MINIMUM_VARIANCE",
    included_asset_ids: [AAPL_ID, MSFT_ID],
    baseline_weights: [
      { asset_id: AAPL_ID, weight: 0.4 },
      { asset_id: MSFT_ID, weight: 0.6 },
    ],
    parameters: {
      source_type: "AD_HOC",
      requested_asset_ids: [AAPL_ID, MSFT_ID],
      bounds: [
        { asset_id: AAPL_ID, minimum: 0, maximum: 1 },
        { asset_id: MSFT_ID, minimum: 0, maximum: 1 },
      ],
      baseline_weights: [
        { asset_id: AAPL_ID, weight: 0.4 },
        { asset_id: MSFT_ID, weight: 0.6 },
      ],
      risk_free_rate_annual: 0.03,
      frontier_points: 25,
      observations: 120,
      covariance_rank: 2,
    },
    result: {
      portfolio: {
        method: "MINIMUM_VARIANCE",
        weights: [
          { asset_id: AAPL_ID, weight: 0.45 },
          { asset_id: MSFT_ID, weight: 0.55 },
        ],
        expected_return: 0.11,
        expected_volatility: 0.16,
        sharpe_ratio: 0.5,
        target_return: null,
      },
      frontier: [],
    },
    warnings: [],
    failure_code: "",
    failure_message: "",
    started_at: "2026-09-17T10:00:00Z",
    completed_at: "2026-09-17T10:00:01Z",
    created_at: "2026-09-17T10:00:00Z",
    provenance: {
      period_start: "2025-01-01",
      period_end_exclusive: "2026-01-01",
      provider: "yfinance",
      price_field: "adjusted_close",
      annualization_factor: 252,
      risk_free_rate_annual: 0.03,
      benchmark_asset_id: null,
      engine_version: "0.2.0",
      method_version: "1.0",
      data_retrieved_at: "2026-09-17T10:00:01Z",
      data_fingerprint: "abc",
    },
    ...overrides,
  };
}

function portfolioResponse() {
  return [
    {
      id: PORTFOLIO_ID,
      name: "Primary portfolio",
      base_currency: "USD",
      benchmark_asset_id: null,
      created_at: "2025-01-02T15:00:00Z",
      updated_at: "2026-09-15T22:00:00Z",
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
      requested_start: "2025-01-01",
      requested_end_exclusive: "2026-01-01",
      effective_start: "2025-01-01",
      effective_end_exclusive: "2026-01-01",
      valuation_cutoff: "2026-01-01T00:00:00Z",
      calculated_at: "2026-01-01T00:00:00Z",
      engine_version: "0.2.0",
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
      holdings: [
        {
          asset_id: AAPL_ID,
          symbol: "AAPL",
          name: "Apple Inc.",
          asset_type: "STOCK",
          currency: "USD",
          quantity: "10",
          current_price: "200",
          current_price_date: "2026-01-01",
          current_price_retrieved_at: null,
          stale_trading_sessions: 0,
          market_value: "2000",
          weight: 0.4,
          weight_unavailable_reason: null,
          selected_period_return: null,
          selected_period_return_unavailable_reason: null,
          contribution_to_return: null,
          contribution_unavailable_reason: null,
          sparkline: [],
          data_quality: "CURRENT",
          warnings: [],
        },
        {
          asset_id: MSFT_ID,
          symbol: "MSFT",
          name: "Microsoft Corp.",
          asset_type: "STOCK",
          currency: "USD",
          quantity: "5",
          current_price: "600",
          current_price_date: "2026-01-01",
          current_price_retrieved_at: null,
          stale_trading_sessions: 0,
          market_value: "3000",
          weight: 0.6,
          weight_unavailable_reason: null,
          selected_period_return: null,
          selected_period_return_unavailable_reason: null,
          contribution_to_return: null,
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
        requested_start: "2025-01-01",
        requested_end_exclusive: "2026-01-01",
        effective_start: "2025-01-01",
        effective_end_exclusive: "2026-01-01",
        current_price_as_of: null,
        period_data_as_of: null,
        calculated_at: "2026-01-01T00:00:00Z",
        current_price_field: "close",
        period_price_field: "adjusted_close",
      },
    },
    movers: null,
    analytics: null,
    review_items: null,
  };
}

function renderPage(initialEntry = "/allocation-lab") {
  return render(
    <QueryClientProvider client={queryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/allocation-lab" element={<AllocationLabPage />} />
          <Route
            path="/portfolios/:portfolioId/allocation-lab"
            element={<AllocationLabPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function waitForLabReady() {
  await screen.findByRole("heading", {
    name: "Allocation source",
  });
}

function installFetch(options: {
  runs?: OptimizationRun[];
  postRun?: OptimizationRun;
  optimizationStatus?: number;
} = {}) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/api/v1/portfolios/")) {
        return new Response(JSON.stringify(portfolioResponse()), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.endsWith("/api/v1/assets/") && (init?.method ?? "GET") === "GET") {
        return new Response(
          JSON.stringify([
            asset(AAPL_ID, "AAPL", "Apple Inc."),
            asset(MSFT_ID, "MSFT", "Microsoft Corp."),
          ]),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      }

      if (url.endsWith("/api/v1/assets/resolve/")) {
        const body = JSON.parse(String(init?.body)) as { symbols: string[] };
        return new Response(
          JSON.stringify({
            provider: "yfinance",
            outcomes: body.symbols.map((symbol) => ({
              symbol,
              status: "RESOLVED",
              asset:
                symbol === "AAPL"
                  ? asset(AAPL_ID, "AAPL", "Apple Inc.")
                  : asset(MSFT_ID, "MSFT", "Microsoft Corp."),
              warning: null,
            })),
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      }

      if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
        return new Response(JSON.stringify(dashboardResponse()), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.endsWith("/api/v1/optimization-runs/") && (init?.method ?? "GET") === "GET") {
        return new Response(JSON.stringify(options.runs ?? []), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.endsWith("/api/v1/optimization-runs/") && init?.method === "POST") {
        const status = options.optimizationStatus ?? 201;
        if (status !== 201) {
          return new Response(
            JSON.stringify({
              code: "VALIDATION_ERROR",
              errors: { non_field_errors: ["Invalid optimization configuration."] },
            }),
            {
              status,
              headers: { "content-type": "application/json" },
            },
          );
        }
        return new Response(JSON.stringify(options.postRun ?? run()), {
          status: 201,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.includes("/api/v1/optimization-runs/run-1/")) {
        return new Response(JSON.stringify(options.postRun ?? run()), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AllocationLabPage", () => {
  it("opens as a standalone ad hoc research workspace", async () => {
    installFetch();
    renderPage();

    await waitForLabReady();
    expect(
      screen.getByRole("button", { name: "Ad hoc portfolio" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Add ticker symbols")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Allocation Lab" }).length,
    ).toBeGreaterThan(0);
  });

  it("resolves ticker text to canonical asset IDs and submits editable configuration", async () => {
    const postRun = run();
    const fetchMock = installFetch({ postRun });
    renderPage();

    await waitForLabReady();

    fireEvent.change(screen.getByLabelText("Add ticker symbols"), {
      target: { value: "aapl, msft" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add canonical assets" }));

    expect(
      await screen.findAllByRole("button", { name: "Remove" }),
    ).toHaveLength(2);

    fireEvent.change(screen.getByLabelText("AAPL baseline weight"), {
      target: { value: "0.4" },
    });
    fireEvent.change(screen.getByLabelText("MSFT baseline weight"), {
      target: { value: "0.6" },
    });
    fireEvent.change(screen.getByLabelText("Annual risk-free rate"), {
      target: { value: "0.03" },
    });
    fireEvent.change(screen.getByLabelText("Analysis start"), {
      target: { value: "2025-01-01" },
    });
    fireEvent.change(screen.getByLabelText("End (exclusive)"), {
      target: { value: "2026-01-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([input, init]) =>
          String(input).endsWith("/api/v1/optimization-runs/") &&
          init?.method === "POST",
      );
      expect(post).toBeDefined();
      const body = JSON.parse(String(post?.[1]?.body)) as Record<string, unknown>;
      expect(body).toMatchObject({
        source_type: "AD_HOC",
        portfolio_id: null,
        asset_ids: [AAPL_ID, MSFT_ID],
        risk_free_rate_annual: 0.03,
        baseline_weights: [
          { asset_id: AAPL_ID, weight: 0.4 },
          { asset_id: MSFT_ID, weight: 0.6 },
        ],
      });
    });

    expect(await screen.findByText("Ad hoc")).toBeInTheDocument();

    const methodologySection = screen
      .getByRole("heading", { name: "Methodology" })
      .closest("section");

    expect(methodologySection).not.toBeNull();
    expect(
      within(methodologySection!).getByText("adjusted_close"),
    ).toBeInTheDocument();
    expect(
      within(methodologySection!).getByText("Mean daily simple return × 252"),
    ).toBeInTheDocument();
  });

  it("imports an owned portfolio without mutating its holdings", async () => {
    const fetchMock = installFetch({
      postRun: run({
        source_type: "PORTFOLIO",
        portfolio_id: PORTFOLIO_ID,
        portfolio_name: "Primary portfolio",
        baseline_weights: [],
        parameters: {
          ...run().parameters,
          source_type: "PORTFOLIO",
          baseline_weights: [],
        },
      }),
    });
    renderPage(`/allocation-lab?portfolio=${PORTFOLIO_ID}`);

    await waitForLabReady();
    const importButton = screen.getByRole("button", {
      name: "Import current holdings",
    });
    await waitFor(() => {
      expect(importButton).toBeEnabled();
    });
    fireEvent.click(importButton);

    expect(await screen.findByText("Apple Inc.")).toBeInTheDocument();
    expect(screen.getByText("Microsoft Corp.")).toBeInTheDocument();
    expect(screen.getByText("40.00%")).toBeInTheDocument();
    expect(screen.getByText("60.00%")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Analysis start"), {
      target: { value: "2025-01-01" },
    });
    fireEvent.change(screen.getByLabelText("End (exclusive)"), {
      target: { value: "2026-01-01" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    await waitFor(() => {
      const post = fetchMock.mock.calls.find(
        ([input, init]) =>
          String(input).endsWith("/api/v1/optimization-runs/") &&
          init?.method === "POST",
      );
      const body = JSON.parse(String(post?.[1]?.body)) as Record<string, unknown>;
      expect(body).toMatchObject({
        source_type: "PORTFOLIO",
        portfolio_id: PORTFOLIO_ID,
        asset_ids: [AAPL_ID, MSFT_ID],
      });
    });
  });

  it("supports the legacy portfolio-scoped route as a compatibility alias", async () => {
    installFetch();
    renderPage(`/portfolios/${PORTFOLIO_ID}/allocation-lab?range=6M`);

    await waitForLabReady();
    expect(
      screen.getByRole("button", { name: "Existing portfolio" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps canonical methodology read-only while configuration remains labeled", async () => {
    installFetch();
    renderPage();
    await waitForLabReady();

    expect(screen.getByRole("heading", { name: "Configuration" })).toBeInTheDocument();
    expect(screen.getByLabelText("Annual risk-free rate")).toBeInTheDocument();
    expect(screen.getByLabelText("Optimization method")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Methodology" })).toBeInTheDocument();
    expect(screen.getByText("Complete-case sample covariance, ddof=1 × 252")).toBeInTheDocument();
    expect(screen.queryByLabelText(/solver tolerance/i)).not.toBeInTheDocument();
  });

  it("renders both ad hoc and portfolio-derived immutable run history", async () => {
    installFetch({
      runs: [
        run({ id: "ad-hoc-run" }),
        run({
          id: "portfolio-run",
          source_type: "PORTFOLIO",
          portfolio_id: PORTFOLIO_ID,
          portfolio_name: "Primary portfolio",
        }),
      ],
    });
    renderPage();
    await waitForLabReady();

    expect(screen.getByText("Ad hoc")).toBeInTheDocument();
    expect(screen.getByText(/Portfolio-derived · Primary portfolio/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Inspect run" })).toHaveLength(2);
  });

  it("surfaces server validation failure without manufacturing a successful result", async () => {
    installFetch({ optimizationStatus: 400 });
    renderPage();

    await waitForLabReady();
    fireEvent.change(screen.getByLabelText("Add ticker symbols"), {
      target: { value: "AAPL" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add canonical assets" }));
    await screen.findByText("Apple Inc.");

    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(
      await screen.findByText("Optimization configuration is invalid"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Expected annual return")).not.toBeInTheDocument();
  });
});
