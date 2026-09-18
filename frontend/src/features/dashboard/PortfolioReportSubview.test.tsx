import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { DashboardSnapshotResult } from "../../types/dashboard";
import { PortfolioReportSubview } from "./PortfolioReportSubview";

vi.mock("./HoldingsPanel", () => ({
  HoldingsPanel: ({ portfolioId }: { portfolioId: string }) => (
    <div>Holdings module for {portfolioId}</div>
  ),
}));

vi.mock("./AllocationPanel", () => ({
  AllocationPanel: () => <div>Allocation module</div>,
}));

vi.mock("./PerformanceHero", () => ({
  PerformanceHero: () => <div>Performance chart module</div>,
}));

vi.mock("./PortfolioReportRisk", () => ({
  PortfolioReportRisk: () => <div>Risk metric module</div>,
}));

vi.mock("../activity/TransactionHistoryPanel", () => ({
  TransactionHistoryPanel: ({ portfolioId }: { portfolioId: string }) => (
    <div>Ledger history for {portfolioId}</div>
  ),
}));

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function snapshot(): DashboardSnapshotResult {
  return {
    snapshot: {
      snapshot_id: "snapshot-1",
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-01-01",
      requested_end_exclusive: "2026-09-19",
      effective_start: "2026-01-02",
      effective_end_exclusive: "2026-09-19",
      valuation_cutoff: "2026-09-18T20:00:00Z",
      calculated_at: "2026-09-18T20:01:00Z",
      engine_version: "test",
      current_data_as_of: "2026-09-18T20:00:00Z",
      historical_data_as_of: "2026-09-18T20:00:00Z",
      analytics_as_of_date: "2026-09-18",
    },
    is_complete: true,
    modules: [
      { module: "SUMMARY", status: "AVAILABLE", error_code: null, detail: null },
      { module: "PERFORMANCE", status: "AVAILABLE", error_code: null, detail: null },
      { module: "ALLOCATION", status: "AVAILABLE", error_code: null, detail: null },
      { module: "HOLDINGS", status: "AVAILABLE", error_code: null, detail: null },
      { module: "MOVERS", status: "AVAILABLE", error_code: null, detail: null },
      { module: "ANALYTICS", status: "AVAILABLE", error_code: null, detail: null },
      { module: "REVIEW_ITEMS", status: "AVAILABLE", error_code: null, detail: null },
    ],
    summary: null,
    performance: {
      summary: {
        starting_value: "10000.00",
        ending_value: "11250.00",
        value_change: "1250.00",
        net_external_flow: "500.00",
        investment_gain_loss: "750.00",
        cumulative_return: 0.075,
        benchmark_cumulative_return: 0.061,
      },
      points: [],
      benchmark_points: [],
      portfolio_data_quality: "CURRENT",
      benchmark_data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id: PORTFOLIO_ID,
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-01-01",
        requested_end_exclusive: "2026-09-19",
        effective_start: "2026-01-02",
        effective_end_exclusive: "2026-09-19",
        data_as_of: "2026-09-18T20:00:00Z",
        calculated_at: "2026-09-18T20:01:00Z",
        engine_version: "test",
        price_field: "adjusted_close",
        benchmark_asset_id: "00000000-0000-0000-0000-000000000010",
        benchmark_symbol: "SPY",
      },
    },
    allocation: null,
    holdings: null,
    movers: null,
    analytics: {
      portfolio_id: PORTFOLIO_ID,
      observations: 170,
      benchmark_observations: 168,
      cumulative_return: 0.075,
      cagr: {
        value: 0.12,
        wealth_ratio: 1.12,
        elapsed_days: 260,
        elapsed_years: 0.71,
        is_short_period: true,
      },
      annualized_volatility: 0.17,
      sharpe: null,
      sortino: null,
      maximum_drawdown: null,
      beta: null,
      benchmark_correlation: {
        value: 0.91,
        observations: 168,
        warnings: [],
      },
      current_allocation: null,
      concentration: {
        largest_position_weight: 0.31,
        herfindahl_hirschman_index: 0.18,
        security_position_count: 8,
        cash_weight: 0.04,
        largest_position_includes_cash: false,
        hhi_includes_cash: true,
        long_only: true,
        weight_sum_tolerance: 1e-9,
      },
      rolling_return_window: 21,
      rolling_returns: [],
      provenance: {
        engine_version: "test",
        as_of_date: "2026-09-18",
        period_start: "2026-01-02",
        period_end: "2026-09-18",
        data_source: "mock",
        price_field: "adjusted_close",
        annualization_factor: 252,
        benchmark: "SPY",
        assumptions: ["Daily observations."],
        warnings: [],
      },
      warnings: [
        {
          code: "INSUFFICIENT_HISTORY",
          message: "One metric has insufficient history.",
          observations: 12,
        },
      ],
    },
    review_items: null,
  };
}

function renderSubview(
  view: "holdings" | "allocation" | "performance" | "risk" | "transactions",
) {
  return render(
    <MemoryRouter>
      <PortfolioReportSubview
        view={view}
        portfolioId={PORTFOLIO_ID}
        snapshot={view === "transactions" ? undefined : snapshot()}
        isLoading={false}
        isFetching={false}
        error={null}
        onRetry={vi.fn()}
      />
    </MemoryRouter>,
  );
}

describe("PortfolioReportSubview", () => {
  it("renders the full holdings module for the stable portfolio UUID", async () => {
    renderSubview("holdings");

    expect(
      screen.getByRole("heading", { name: "Holdings" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(`Holdings module for ${PORTFOLIO_ID}`),
    ).toBeInTheDocument();
  });

  it("renders server-returned performance accounting details without recomputing them", () => {
    renderSubview("performance");

    expect(
      screen.getByRole("heading", { name: "Performance" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Performance chart module")).toBeInTheDocument();
    expect(screen.getByText("Net external flow")).toBeInTheDocument();
    expect(screen.getByText("$500.00")).toBeInTheDocument();
    expect(screen.getByText("Benchmark return")).toBeInTheDocument();
    expect(screen.getByText("+6.10%")).toBeInTheDocument();
  });

  it("renders risk provenance and warnings without inventing threshold statuses", () => {
    renderSubview("risk");

    expect(screen.getByRole("heading", { name: "Risk" })).toBeInTheDocument();
    expect(screen.getByText("Risk metric module")).toBeInTheDocument();
    expect(screen.getByText("Calculation context")).toBeInTheDocument();
    expect(screen.getByText(/Benchmark\s+SPY/)).toBeInTheDocument();
    expect(
      screen.getByText("One metric has insufficient history."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Within range")).not.toBeInTheDocument();
    expect(screen.queryByText("Watch")).not.toBeInTheDocument();
  });

  it("renders transactions as read-only report detail and hands mutation work to Activity", () => {
    renderSubview("transactions");

    expect(
      screen.getByRole("heading", { name: "Transactions" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(`Ledger history for ${PORTFOLIO_ID}`),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open Activity & Transactions" }),
    ).toHaveAttribute("href", `/activity?portfolio=${PORTFOLIO_ID}`);
    expect(
      screen.getByText(/editing, deletion, and reconciliation are not supported/i),
    ).toBeInTheDocument();
  });
});
