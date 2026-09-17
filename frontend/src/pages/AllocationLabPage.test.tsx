import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
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
  AllocationComparisonChart: ({ rows }: { rows: unknown[] }) => (
    <div data-testid="allocation-comparison-chart">{JSON.stringify(rows)}</div>
  ),
}));

vi.mock("../components/charts/EfficientFrontierChart", () => ({
  EfficientFrontierChart: ({
    points,
  }: {
    points: Array<{ expected_return: number; expected_volatility: number }>;
  }) => (
    <div data-testid="efficient-frontier-chart">
      {JSON.stringify(points)}
    </div>
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

function dashboardResponse(holdings = true) {
  return {
    snapshot: {
      snapshot_id: "snapshot-1",
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "yfinance",
      requested_start: "2026-03-17",
      requested_end_exclusive: "2026-09-18",
      effective_start: "2026-03-17",
      effective_end_exclusive: "2026-09-18",
      valuation_cutoff: "2026-09-17T16:00:00Z",
      calculated_at: "2026-09-17T16:00:00Z",
      engine_version: "0.1.0",
      current_data_as_of: "2026-09-16T00:00:00Z",
      historical_data_as_of: "2026-09-16T00:00:00Z",
      analytics_as_of_date: "2026-09-16",
    },
    is_complete: true,
    modules: [],
    summary: null,
    performance: null,
    allocation: null,
    holdings: {
      holdings: holdings
        ? [
            {
              asset_id: AAPL_ID,
              symbol: "AAPL",
              name: "Apple Inc.",
              asset_type: "STOCK",
              currency: "USD",
              quantity: "10",
              current_price: "200",
              current_price_date: "2026-09-16",
              current_price_retrieved_at: "2026-09-17T15:00:00Z",
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
              current_price_date: "2026-09-16",
              current_price_retrieved_at: "2026-09-17T15:00:00Z",
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
          ]
        : [],
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id: PORTFOLIO_ID,
        base_currency: "USD",
        provider: "yfinance",
        requested_start: "2026-03-17",
        requested_end_exclusive: "2026-09-18",
        effective_start: "2026-03-17",
        effective_end_exclusive: "2026-09-18",
        current_price_as_of: "2026-09-16",
        period_data_as_of: "2026-09-16",
        calculated_at: "2026-09-17T16:00:00Z",
        current_price_field: "adjusted_close",
        period_price_field: "adjusted_close",
      },
    },
    movers: null,
    analytics: null,
    review_items: null,
  };
}

function successfulRun(
  method: OptimizationRun["method"],
  overrides: Partial<OptimizationRun> = {},
): OptimizationRun {
  return {
    id: `run-${method.toLowerCase()}`,
    portfolio_id: PORTFOLIO_ID,
    status: "SUCCEEDED",
    method,
    included_asset_ids: [AAPL_ID, MSFT_ID],
    parameters: {
      requested_asset_ids: [AAPL_ID, MSFT_ID],
      bounds: [
        { asset_id: AAPL_ID, minimum: 0, maximum: 0.7 },
        { asset_id: MSFT_ID, minimum: 0, maximum: 1 },
      ],
      frontier_points: 25,
      observations: 120,
      covariance_rank: 2,
    },
    result: {
      portfolio:
        method === "EFFICIENT_FRONTIER"
          ? null
          : {
              method,
              weights: [
                { asset_id: AAPL_ID, weight: 0.35 },
                { asset_id: MSFT_ID, weight: 0.65 },
              ],
              expected_return: 0.123456,
              expected_volatility: 0.176543,
              sharpe_ratio: method === "EQUAL_WEIGHT" ? null : 0.6999,
              target_return: null,
            },
      frontier:
        method === "EFFICIENT_FRONTIER"
          ? [
              {
                method: "EFFICIENT_FRONTIER",
                weights: [
                  { asset_id: AAPL_ID, weight: 0.3 },
                  { asset_id: MSFT_ID, weight: 0.7 },
                ],
                expected_return: 0.1,
                expected_volatility: 0.12,
                sharpe_ratio: 0.83,
                target_return: 0.1,
              },
              {
                method: "EFFICIENT_FRONTIER",
                weights: [
                  { asset_id: AAPL_ID, weight: 0.5 },
                  { asset_id: MSFT_ID, weight: 0.5 },
                ],
                expected_return: 0.14,
                expected_volatility: 0.18,
                sharpe_ratio: 0.78,
                target_return: 0.14,
              },
            ]
          : [],
    },
    warnings: [
      {
        code: "SOURCE_WARNING",
        message: "One provider observation carried a source warning.",
      },
    ],
    failure_code: "",
    failure_message: "",
    started_at: "2026-09-17T10:00:00Z",
    completed_at: "2026-09-17T10:00:01Z",
    created_at: "2026-09-17T10:00:00Z",
    provenance: {
      period_start: "2026-03-01",
      period_end_exclusive: "2026-09-01",
      provider: "yfinance",
      price_field: "adjusted_close",
      annualization_factor: 252,
      risk_free_rate_annual: 0,
      benchmark_asset_id: null,
      engine_version: "0.1.0",
      method_version: "1.0",
      data_retrieved_at: "2026-09-17T10:00:00Z",
      data_fingerprint: "feedface",
    },
    ...overrides,
  };
}

function failedRun(code: string, message: string): OptimizationRun {
  return {
    ...successfulRun("MINIMUM_VARIANCE"),
    id: `failed-${code}`,
    status: "FAILED",
    result: null,
    warnings: [],
    failure_code: code,
    failure_message: message,
  };
}

function renderPage(initialEntry = `/portfolios/${PORTFOLIO_ID}/allocation-lab?range=6M`) {
  return render(
    <QueryClientProvider client={queryClient()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/portfolios/:portfolioId/allocation-lab"
            element={<AllocationLabPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function installFetch(options: {
  holdings?: boolean;
  existingRuns?: OptimizationRun[];
  postRun?: OptimizationRun;
  postStatus?: number;
  postPayload?: unknown;
}) {
  let runs = [...(options.existingRuns ?? [])];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.endsWith("/api/v1/portfolios/")) {
      return new Response(JSON.stringify(portfolioResponse()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (url.includes(`/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`)) {
      return new Response(JSON.stringify(dashboardResponse(options.holdings ?? true)), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (url.endsWith("/api/v1/optimization-runs/") && init?.method === "POST") {
      if (options.postStatus && options.postStatus !== 201) {
        return new Response(JSON.stringify(options.postPayload ?? {}), {
          status: options.postStatus,
          headers: { "content-type": "application/json" },
        });
      }

      const result = options.postRun ?? successfulRun("MINIMUM_VARIANCE");
      runs = [result, ...runs.filter((run) => run.id !== result.id)];
      return new Response(JSON.stringify(result), {
        status: 201,
        headers: { "content-type": "application/json" },
      });
    }

    if (url.endsWith("/api/v1/optimization-runs/")) {
      return new Response(JSON.stringify(runs), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    const detailMatch = url.match(/\/api\/v1\/optimization-runs\/([^/]+)\/$/);
    if (detailMatch) {
      const result = runs.find((run) => run.id === detailMatch[1]);
      return new Response(JSON.stringify(result ?? { code: "NOT_FOUND", detail: "Missing." }), {
        status: result ? 200 : 404,
        headers: { "content-type": "application/json" },
      });
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function waitForControls() {
  expect(
    await screen.findByRole("heading", {
      name: "Create a persisted optimization run",
    }),
  ).toBeInTheDocument();
  expect(
    await screen.findByLabelText("AAPL maximum weight"),
  ).toBeEnabled();
}

function setFixedPeriod() {
  fireEvent.change(screen.getByLabelText("Start"), {
    target: { value: "2026-03-01" },
  });
  fireEvent.change(screen.getByLabelText("End (exclusive)"), {
    target: { value: "2026-09-01" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("AllocationLabPage", () => {
  it("preserves portfolio and range context across Allocation Lab navigation", async () => {
    installFetch({});
    renderPage();
    await waitForControls();

    expect(screen.getByRole("link", { name: "← Back to dashboard" })).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );
    expect(screen.getByRole("link", { name: "Portfolio analysis" })).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
    );
  });

  it("submits canonical asset IDs, explicit bounds, method, and period without frontend financial assumptions", async () => {
    const fetchMock = installFetch({
      postRun: successfulRun("MAXIMUM_SHARPE"),
    });
    renderPage();
    await waitForControls();
    setFixedPeriod();

    fireEvent.change(screen.getByLabelText("Optimization method"), {
      target: { value: "MAXIMUM_SHARPE" },
    });
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(
      await screen.findByRole("heading", { name: "Maximum Sharpe" }),
    ).toBeInTheDocument();

    const postCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        String(input).endsWith("/api/v1/optimization-runs/") && init?.method === "POST",
    );
    expect(postCall).toBeDefined();

    const request = JSON.parse(String(postCall?.[1]?.body)) as Record<string, unknown>;
    expect(request).toEqual({
      portfolio_id: PORTFOLIO_ID,
      method: "MAXIMUM_SHARPE",
      start: "2026-03-01",
      end: "2026-09-01",
      asset_ids: [AAPL_ID, MSFT_ID],
      bounds: [
        { asset_id: AAPL_ID, minimum: 0, maximum: 0.7 },
        { asset_id: MSFT_ID, minimum: 0, maximum: 1 },
      ],
    });
    expect(request).not.toHaveProperty("risk_free_rate_annual");
  });

  it.each([
    ["EQUAL_WEIGHT", "Equal weight"],
    ["MINIMUM_VARIANCE", "Minimum variance"],
    ["MAXIMUM_SHARPE", "Maximum Sharpe"],
  ] as const)("renders a successful persisted %s run", async (method, label) => {
    installFetch({ postRun: successfulRun(method) });
    renderPage();
    await waitForControls();
    setFixedPeriod();
    fireEvent.change(screen.getByLabelText("Optimization method"), {
      target: { value: method },
    });
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(await screen.findByRole("heading", { name: label })).toBeInTheDocument();
    expect(screen.getAllByText("Succeeded").length).toBeGreaterThan(0);
  });

  it.each([
    ["PENDING", "Optimization pending"],
    ["RUNNING", "Optimization running"],
  ] as const)("renders persisted %s status without pretending success", async (status, heading) => {
    installFetch({
      postRun: {
        ...successfulRun("MINIMUM_VARIANCE"),
        id: `run-${status.toLowerCase()}`,
        status,
        result: null,
        warnings: [],
        completed_at: null,
      },
    });
    renderPage();
    await waitForControls();
    setFixedPeriod();
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.queryByText("Expected annual return")).not.toBeInTheDocument();
  });

  it("compares current allocation only with matching successful persisted runs", async () => {
    installFetch({
      existingRuns: [
        successfulRun("EQUAL_WEIGHT"),
        successfulRun("MINIMUM_VARIANCE"),
        successfulRun("MAXIMUM_SHARPE"),
      ],
    });
    renderPage();
    await waitForControls();
    expect(await screen.findByText("Recent persisted runs")).toBeInTheDocument();
    setFixedPeriod();
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });

    const chart = screen.getByTestId("allocation-comparison-chart");
    expect(chart).toHaveTextContent('"currentWeight":0.4');
    expect(chart).toHaveTextContent('"equalWeight":0.35');
    expect(chart).toHaveTextContent('"minimumVarianceWeight":0.35');
    expect(chart).toHaveTextContent('"maximumSharpeWeight":0.35');
  });

  it("renders exact server metrics, nullable values, warnings, and provenance without recomputation", async () => {
    installFetch({
      postRun: successfulRun("EQUAL_WEIGHT"),
    });
    renderPage();
    await waitForControls();
    setFixedPeriod();

    fireEvent.change(screen.getByLabelText("Optimization method"), {
      target: { value: "EQUAL_WEIGHT" },
    });
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(await screen.findByText("12.35%")).toBeInTheDocument();
    expect(screen.getByText("17.65%")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
    expect(
      screen.getByText("One provider observation carried a source warning."),
    ).toBeInTheDocument();
    expect(screen.getByText("yfinance")).toBeInTheDocument();
    expect(screen.getByText("feedface")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();
  });

  it("passes every server-provided efficient-frontier point to the chart without interpolation", async () => {
    installFetch({
      postRun: successfulRun("EFFICIENT_FRONTIER"),
    });
    renderPage();
    await waitForControls();
    setFixedPeriod();

    fireEvent.change(screen.getByLabelText("Optimization method"), {
      target: { value: "EFFICIENT_FRONTIER" },
    });
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });
    fireEvent.change(screen.getByLabelText("Frontier points"), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    const chart = await screen.findByTestId("efficient-frontier-chart");
    expect(chart).toHaveTextContent('"expected_return":0.1');
    expect(chart).toHaveTextContent('"expected_volatility":0.12');
    expect(chart).toHaveTextContent('"expected_return":0.14');
    expect(chart).toHaveTextContent('"expected_volatility":0.18');
  });

  it.each([
    ["OPTIMIZATION_INFEASIBLE", "Weight constraints are infeasible."],
    ["OPTIMIZATION_INSUFFICIENT_DATA", "Insufficient complete-case history."],
    ["OPTIMIZATION_SOLVER_FAILED", "The solver did not converge."],
    ["OPTIMIZATION_POST_VALIDATION_FAILED", "Solver output failed independent validation."],
    ["OPTIMIZATION_SINGULAR_COVARIANCE", "Covariance matrix could not support a valid solve."],
    ["ASSET_UNSUPPORTED", "One selected asset is outside the supported optimization universe."],
    ["MARKET_DATA_UNAVAILABLE", "Required adjusted-close history is unavailable."],
  ])("renders persisted FAILED diagnostics for %s", async (code, message) => {
    installFetch({ postRun: failedRun(code, message) });
    renderPage();
    await waitForControls();
    setFixedPeriod();
    fireEvent.change(screen.getByLabelText("AAPL maximum weight"), {
      target: { value: "0.7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(
      await screen.findByRole("heading", { name: "Optimization run failed" }),
    ).toBeInTheDocument();
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByText(humanizeForTest(code))).toBeInTheDocument();
  });

  it.each([
    [403, "Portfolio access denied"],
    [404, "Portfolio or optimization run not found"],
    [503, "Optimization data provider unavailable"],
    [500, "Allocation Lab could not load"],
  ])("renders accessible transport state for HTTP %s", async (status, title) => {
    installFetch({
      postStatus: status,
      postPayload: { code: "ERROR", detail: `Request failed ${status}.` },
    });
    renderPage();
    await waitForControls();
    setFixedPeriod();
    fireEvent.click(screen.getByRole("button", { name: "Run optimization" }));

    expect(await screen.findByText(title)).toBeInTheDocument();
    expect(screen.getByText(`Request failed ${status}.`)).toBeInTheDocument();
  });

  it("renders explicit no-eligible-holdings state", async () => {
    installFetch({ holdings: false });
    renderPage();

    expect(await screen.findByText("No eligible holdings")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run optimization" })).not.toBeInTheDocument();
  });

  it("exposes keyboard-addressable labeled optimization controls", async () => {
    installFetch({});
    renderPage();
    await waitForControls();

    expect(screen.getByLabelText("Start")).toBeInTheDocument();
    expect(screen.getByLabelText("End (exclusive)")).toBeInTheDocument();
    expect(screen.getByLabelText("Optimization method")).toBeInTheDocument();
    expect(screen.getByLabelText(/AAPL\s+Apple Inc\./)).toBeInTheDocument();
    expect(screen.getByLabelText("AAPL minimum weight")).toBeInTheDocument();
    expect(screen.getByLabelText("AAPL maximum weight")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run optimization" })).toBeEnabled();
  });
});

function humanizeForTest(code: string): string {
  return code
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/^./, (letter) => letter.toUpperCase());
}
