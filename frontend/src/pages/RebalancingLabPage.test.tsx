import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { RebalancingLabPage } from "./RebalancingLabPage";

vi.mock("../components/charts/RebalanceValueComparisonChart", () => ({
  RebalanceValueComparisonChart: () => <div>Historical value comparison chart</div>,
}));

const PORTFOLIO_ID = "00000000-0000-0000-0000-00000000d001";
const TARGET_ID = "00000000-0000-0000-0000-00000000b001";
const AAPL_ID = "00000000-0000-0000-0000-00000000a101";
const MSFT_ID = "00000000-0000-0000-0000-00000000a102";

const target = {
  id: TARGET_ID,
  portfolio_id: PORTFOLIO_ID,
  name: "Minimum variance target",
  source_optimization_run_id: "run-1",
  weights: [
    { asset_id: AAPL_ID, is_cash: false, weight: 0.55 },
    { asset_id: MSFT_ID, is_cash: false, weight: 0.45 },
  ],
  created_at: "2026-09-16T16:00:00Z",
  updated_at: "2026-09-16T16:00:00Z",
};

const optimizationRun = {
  id: "run-1",
  source_type: "PORTFOLIO",
  portfolio_id: PORTFOLIO_ID,
  portfolio_name: "Deterministic Sample Portfolio",
  status: "SUCCEEDED",
  method: "MINIMUM_VARIANCE",
  included_asset_ids: [AAPL_ID, MSFT_ID],
  baseline_weights: [],
  parameters: {
    source_type: "PORTFOLIO",
    requested_asset_ids: null,
    bounds: [],
    baseline_weights: [],
    risk_free_rate_annual: 0,
    frontier_points: 25,
  },
  result: {
    portfolio: {
      method: "MINIMUM_VARIANCE",
      weights: [
        { asset_id: AAPL_ID, weight: 0.55 },
        { asset_id: MSFT_ID, weight: 0.45 },
      ],
      expected_return: 0.1,
      expected_volatility: 0.15,
      sharpe_ratio: 0.66,
      target_return: null,
    },
    frontier: [],
  },
  warnings: [],
  failure_code: "",
  failure_message: "",
  started_at: "2026-09-16T15:00:00Z",
  completed_at: "2026-09-16T15:00:01Z",
  created_at: "2026-09-16T15:00:00Z",
  provenance: {
    period_start: "2026-02-02",
    period_end_exclusive: "2026-09-16",
    provider: "csv",
    price_field: "adjusted_close",
    annualization_factor: 252,
    risk_free_rate_annual: 0,
    benchmark_asset_id: null,
    engine_version: "0.1.0.dev0",
    method_version: "1",
    data_retrieved_at: "2026-09-16T15:00:00Z",
    data_fingerprint: "fixture",
  },
};

const simulation = {
  id: "simulation-1",
  portfolio_id: PORTFOLIO_ID,
  target_allocation_id: TARGET_ID,
  as_of: "2026-09-16T16:00:00Z",
  provider: "csv",
  price_field: "close",
  valuation_retrieved_at: "2026-09-16T16:00:00Z",
  drift_threshold: 0.05,
  schedule: "",
  previous_rebalance_date: null,
  result: {
    total_investable_value: 125000,
    current_weight_sum: 1,
    target_weight_sum: 1,
    lines: [
      {
        asset_id: AAPL_ID,
        is_cash: false,
        current_value: 75000,
        target_value: 68750,
        current_weight: 0.6,
        target_weight: 0.55,
        absolute_drift: 0.05,
        relative_drift: 0.090909,
        trade_notional: -6250,
        direction: "SELL",
      },
      {
        asset_id: MSFT_ID,
        is_cash: false,
        current_value: 45000,
        target_value: 56250,
        current_weight: 0.36,
        target_weight: 0.45,
        absolute_drift: -0.09,
        relative_drift: -0.2,
        trade_notional: 11250,
        direction: "BUY",
      },
      {
        asset_id: null,
        is_cash: true,
        current_value: 5000,
        target_value: 0,
        current_weight: 0.04,
        target_weight: 0,
        absolute_drift: 0.04,
        relative_drift: null,
        trade_notional: -5000,
        direction: "SELL",
      },
    ],
    rules: {
      threshold: 0.05,
      threshold_triggered: true,
      schedule: null,
      previous_rebalance_date: null,
      decision_date: "2026-09-16",
      schedule_due: false,
    },
  },
  warnings: [],
  created_at: "2026-09-16T16:00:01Z",
};

function policy(name: string, schedule: string | null, endingValue: number) {
  return {
    name,
    schedule,
    threshold: name === "threshold" ? 0.05 : null,
    summary: {
      initial_value: 100000,
      ending_value: endingValue,
      cumulative_return: endingValue / 100000 - 1,
      rebalance_count: 1,
      trade_count: 2,
      maximum_absolute_drift: 0.08,
      turnover: 0.21,
      commission_cost: 10,
      slippage_cost: 20,
      total_cost: 30,
    },
    snapshots: [
      {
        trade_date: "2026-02-02",
        total_value: 100000,
        cash_value: 60000,
        period_return: null,
        lines: [
          {
            asset_id: AAPL_ID,
            is_cash: false,
            market_value: 22000,
            weight: 0.22,
            target_weight: 0.55,
            absolute_drift: -0.33,
            relative_drift: -0.6,
          },
        ],
      },
      {
        trade_date: "2026-04-01",
        total_value: endingValue,
        cash_value: 1000,
        period_return: 0.01,
        lines: [
          {
            asset_id: AAPL_ID,
            is_cash: false,
            market_value: endingValue * 0.55,
            weight: 0.55,
            target_weight: 0.55,
            absolute_drift: 0,
            relative_drift: 0,
          },
        ],
      },
    ],
    events: [
      {
        trigger: schedule ?? "THRESHOLD",
        decision_date: "2026-03-31",
        execution_date: "2026-04-01",
        pre_trade_value: 101000,
        post_trade_value: 100970,
        turnover: 0.21,
        commission_cost: 10,
        slippage_cost: 20,
        decision_lines: [],
        trades: [
          {
            asset_id: AAPL_ID,
            direction: "BUY",
            quantity: 10,
            reference_price: 120,
            fill_price: 120.12,
            fill_notional: 1201.2,
            commission_cost: 1.2,
            slippage_cost: 1.2,
          },
        ],
      },
    ],
    warnings: [],
  };
}

const comparison = {
  id: "comparison-1",
  portfolio_id: PORTFOLIO_ID,
  target_allocation_id: TARGET_ID,
  period_start: "2026-02-02",
  period_end: "2026-09-15",
  provider: "csv",
  price_field: "adjusted_close",
  retrieved_at: "2026-09-16T15:00:00Z",
  drift_threshold: 0.05,
  commission_rate: 0.001,
  slippage_rate: 0.002,
  engine_version: "0.1.0.dev0",
  result: {
    period_start: "2026-02-02",
    period_end: "2026-09-15",
    aligned_dates: ["2026-02-02", "2026-04-01"],
    initial_state: { cash: 60000, positions: [] },
    target_weights: [
      { asset_id: AAPL_ID, is_cash: false, weight: 0.55 },
      { asset_id: MSFT_ID, is_cash: false, weight: 0.45 },
    ],
    assumptions: {
      price_field: "adjusted_close",
      execution_timing: "decision_at_t_execute_at_next_aligned_observation",
      commission_rate: 0.001,
      slippage_rate: 0.002,
      turnover_convention: "gross executed fill notional divided by pre-trade portfolio value",
      later_actual_ledger_activity: "ignored_after_initial_state",
    },
    policies: [
      policy("annual", "ANNUAL", 105000),
      policy("quarterly", "QUARTERLY", 106000),
      policy("threshold", null, 107000),
    ],
    provenance: {
      provider: "csv",
      retrieved_at: "2026-09-16T15:00:00Z",
      engine_version: "0.1.0.dev0",
      requested_period_start: "2026-02-02",
      requested_period_end: "2026-09-15",
    },
  },
  warnings: [
    {
      code: "ACTUAL_LEDGER_ACTIVITY_IGNORED",
      message: "Later real portfolio transactions were not applied to this hypothetical path.",
    },
  ],
  created_at: "2026-09-16T16:10:00Z",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function renderLab(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal("fetch", fetchMock);
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "user-1",
      email: "owner@example.com",
      first_name: "Portfolio",
      last_name: "Owner",
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/rebalancing-lab?portfolio=${PORTFOLIO_ID}&target=${TARGET_ID}`]}>
        <Routes>
          <Route path="/rebalancing-lab" element={<RebalancingLabPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function baseFetch({ includeTarget = true, includeRun = true } = {}) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/v1/portfolios/")) {
      return jsonResponse([
        {
          id: PORTFOLIO_ID,
          name: "Deterministic Sample Portfolio",
          base_currency: "USD",
          benchmark_asset_id: null,
          ledger_inception_at: "2026-01-02T14:00:00Z",
          created_at: "2026-01-02T14:00:00Z",
          updated_at: "2026-09-16T16:00:00Z",
        },
      ]);
    }
    if (url.endsWith("/api/v1/target-allocations/")) {
      if (method === "POST") {
        return jsonResponse(target, 201);
      }
      return jsonResponse(includeTarget ? [target] : []);
    }
    if (url.endsWith("/api/v1/optimization-runs/")) {
      return jsonResponse(includeRun ? [optimizationRun] : []);
    }
    if (url.endsWith("/api/v1/assets/")) {
      return jsonResponse([
        { id: AAPL_ID, symbol: "AAPL", name: "Apple Inc.", asset_type: "STOCK", exchange: "NASDAQ", currency: "USD" },
        { id: MSFT_ID, symbol: "MSFT", name: "Microsoft Corporation", asset_type: "STOCK", exchange: "NASDAQ", currency: "USD" },
      ]);
    }
    if (url.endsWith("/api/v1/historical-rebalance-comparisons/")) {
      if (method === "POST") {
        return jsonResponse(comparison, 201);
      }
      return jsonResponse([]);
    }
    if (url.endsWith("/api/v1/rebalance-simulations/") && method === "POST") {
      return jsonResponse(simulation, 201);
    }
    throw new Error(`Unexpected request: ${method} ${url}`);
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RebalancingLabPage", () => {
  it("offers target creation from a successful portfolio optimization run", async () => {
    const fetchMock = baseFetch({ includeTarget: false, includeRun: true });
    renderLab(fetchMock);

    expect(await screen.findByRole("heading", { name: "Rebalancing Lab" })).toBeInTheDocument();
    expect(await screen.findByLabelText("Successful optimization run")).toBeInTheDocument();
    expect(
      screen.getByText(/No saved targets exist for this portfolio yet\./),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Successful optimization run"), {
      target: { value: "run-1" },
    });
    fireEvent.change(screen.getByLabelText("Target name"), {
      target: { value: "Saved minimum variance target" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save target" }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          ([input, init]) =>
            String(input).endsWith("/api/v1/target-allocations/") &&
            init?.method === "POST",
        ),
      ).toBe(true);
    });
  });

  it("shows server-provided current drift and historical policy results with timing, provenance, and warnings", async () => {
    renderLab(baseFetch());

    await screen.findByRole("heading", { name: "Rebalancing Lab" });
    const simulateButton = await screen.findByRole("button", {
      name: "Simulate current rebalance",
    });
    await waitFor(() => {
      expect(simulateButton).toBeEnabled();
    });
    fireEvent.click(simulateButton);

    expect(await screen.findByText("Triggered")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText(/SELL/)).toBeInTheDocument();
    expect(screen.getByText(/BUY/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Historical period start"), {
      target: { value: "2026-02-02" },
    });
    fireEvent.change(screen.getByLabelText("Historical period end"), {
      target: { value: "2026-09-15" },
    });
    fireEvent.change(screen.getByLabelText("Commission rate"), {
      target: { value: "0.001" },
    });
    fireEvent.change(screen.getByLabelText("Slippage rate"), {
      target: { value: "0.002" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run historical comparison" }));

    expect(await screen.findByRole("region", { name: "Historical rebalancing comparison results" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Annual" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Quarterly" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Drift threshold" })).toBeInTheDocument();
    expect(screen.getByText("Historical value comparison chart")).toBeInTheDocument();

    const eventTable = screen.getByRole("table", {
      name: "Rebalance decision and execution events",
    });
    expect(within(eventTable).getByText("Mar 31, 2026")).toBeInTheDocument();
    expect(within(eventTable).getByText("Apr 1, 2026")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Historical comparison assumptions and provenance" })).toHaveTextContent("adjusted_close");
    expect(screen.getByRole("region", { name: "Historical comparison assumptions and provenance" })).toHaveTextContent("csv");
    expect(screen.getByLabelText("Rebalancing warnings")).toHaveTextContent("Actual ledger activity ignored");
    expect(screen.getByLabelText("Rebalancing warnings")).toHaveTextContent("not applied");
  });
});
