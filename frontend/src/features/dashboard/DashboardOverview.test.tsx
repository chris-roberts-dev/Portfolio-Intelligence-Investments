import {
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { DashboardSnapshotResult } from "../../types/dashboard";
import { DashboardOverview } from "./DashboardOverview";

vi.mock(
  "../../components/charts/PerformanceChart",
  () => ({
    PerformanceChart: () => (
      <div data-testid="performance-chart">
        Chart
      </div>
    ),
  }),
);

vi.mock("./AllocationPanel", () => ({
  AllocationPanel: () => (
    <div data-testid="allocation-panel">
      Allocation panel
    </div>
  ),
}));

vi.mock("./HoldingsPanel", () => ({
  HoldingsPanel: () => (
    <div data-testid="holdings-panel">
      Holdings panel
    </div>
  ),
}));

vi.mock("./MoversPanel", () => ({
  MoversPanel: () => (
    <div data-testid="movers-panel">
      Movers panel
    </div>
  ),
}));

vi.mock("./ReviewItemsPanel", () => ({
  ReviewItemsPanel: () => (
    <div data-testid="review-items-panel">
      Review items panel
    </div>
  ),
}));

function snapshotFixture(): DashboardSnapshotResult {
  return {
    snapshot: {
      snapshot_id:
        "00000000-0000-0000-0000-000000000001",
      portfolio_id:
        "00000000-0000-0000-0000-000000000002",
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      valuation_cutoff:
        "2026-09-15T22:00:00Z",
      calculated_at:
        "2026-09-15T22:00:00Z",
      engine_version: "0.1.0.dev0",
      current_data_as_of:
        "2026-09-15T21:55:00Z",
      historical_data_as_of:
        "2026-09-15T21:55:00Z",
      analytics_as_of_date: "2026-09-15",
    },
    is_complete: true,
    modules: [
      {
        module: "SUMMARY",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "PERFORMANCE",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "ALLOCATION",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "HOLDINGS",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "MOVERS",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
    ],
    performance: {
      summary: {
        starting_value: "1000.00",
        ending_value: "1100.00",
        value_change: "100.00",
        net_external_flow: "0.00",
        investment_gain_loss: "100.00",
        cumulative_return: 0.1,
        benchmark_cumulative_return: null,
      },
      points: [
        {
          observation_date: "2026-09-01",
          portfolio_value: "1000.00",
          net_external_flow: "0.00",
          daily_return: null,
          cumulative_return: 0,
          data_quality: "CURRENT",
          warnings: [],
        },
        {
          observation_date: "2026-09-15",
          portfolio_value: "1100.00",
          net_external_flow: "0.00",
          daily_return: 0.1,
          cumulative_return: 0.1,
          data_quality: "CURRENT",
          warnings: [],
        },
      ],
      benchmark_points: [],
      portfolio_data_quality: "CURRENT",
      benchmark_data_quality: null,
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        effective_start: "2026-09-01",
        effective_end_exclusive:
          "2026-09-16",
        data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        engine_version: "0.1.0.dev0",
        price_field: "adjusted_close",
        benchmark_asset_id: null,
        benchmark_symbol: null,
      },
    },
    summary: {
      metrics: {
        total_market_value: "1100.00",
        total_market_value_unavailable_reason:
          null,
        net_contributions: "1000.00",
        cost_basis: "900.00",
        cash_balance: "100.00",
        cash_percentage: "0.0909090909",
        cash_percentage_unavailable_reason:
          null,
        unrealized_gain_loss: "100.00",
        unrealized_gain_loss_unavailable_reason:
          null,
        selected_period_realized_gain_loss:
          "25.00",
        selected_period_realized_gain_loss_unavailable_reason:
          null,
        selected_period_income_received:
          "10.00",
        selected_period_income_unavailable_reason:
          null,
      },
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        ledger_as_of:
          "2026-09-15T22:00:00Z",
        current_price_data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        current_price_field: "close",
        accounting_method:
          "WEIGHTED_AVERAGE_BOOK_COST_V1",
        accounting_assumptions: [],
        selected_period_transaction_timezone:
          "UTC",
        net_contributions_scope:
          "LIFETIME_THROUGH_LEDGER_AS_OF",
        selected_period_accounting_scope:
          "REQUESTED_RANGE_INTERSECTED_WITH_LEDGER_AS_OF",
      },
    },
    allocation: {
      allocation_available: true,
      groups: [
        {
          key: "STOCK",
          label: "Stocks",
          is_cash: false,
          asset_count: 1,
          market_value: "1000.00",
          weight: 0.9090909091,
        },
        {
          key: "CASH",
          label: "Cash",
          is_cash: true,
          asset_count: 0,
          market_value: "100.00",
          weight: 0.0909090909,
        },
      ],
      totals: {
        total_market_value: "1100.00",
        invested_value: "1000.00",
        cash_value: "100.00",
        invested_weight: 0.9090909091,
        cash_weight: 0.0909090909,
      },
      data_quality: "CURRENT",
      unavailable_reason: null,
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        as_of:
          "2026-09-15T22:00:00Z",
        data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        price_field: "close",
        grouping_dimension: "ASSET_CLASS",
        supported_grouping_dimensions: [
          "ASSET_CLASS",
        ],
        grouping_source: "Asset.asset_type",
        ordering_rule:
          "SECURITY_WEIGHT_DESC_THEN_GROUP_KEY_CASH_LAST_V1",
        other_grouping_applied: false,
        other_grouping_threshold: null,
        other_grouping_rule:
          "No Other aggregation is applied in the MVP.",
        weight_sum_tolerance: 1e-8,
      },
    },
    holdings: {
      holdings: [],
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        effective_start: "2026-09-01",
        effective_end_exclusive:
          "2026-09-16",
        current_price_as_of:
          "2026-09-15T21:55:00Z",
        period_data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        current_price_field: "close",
        period_price_field:
          "adjusted_close",
      },
    },
    movers: {
      top_gainers: [],
      top_losers: [],
      largest_contributors: [],
      largest_detractors: [],
      reconciliation: {
        status: "AVAILABLE",
        periods: 1,
        cumulative_return: 0.1,
        asset_contribution_total: 0.1,
        unattributed_contribution: 0,
        reconciliation_error: 0,
        unavailable_reason: null,
      },
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        effective_start: "2026-09-01",
        effective_end_exclusive:
          "2026-09-16",
        current_price_as_of:
          "2026-09-15T21:55:00Z",
        period_data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        current_price_field: "close",
        period_price_field:
          "adjusted_close",
        attribution_method:
          "ASSET_PNL_WEALTH_LINKED_V1",
        engine_version: "0.1.0.dev0",
      },
    },
    analytics: null,
    review_items: null,
  };
}

describe("DashboardOverview", () => {
  it("renders performance, summary, allocation, holdings, movers, and review items", async () => {
    render(
      <MemoryRouter initialEntries={["/portfolios/portfolio-1/dashboard?range=3Y&view=report"]}>
        <DashboardOverview
          snapshot={snapshotFixture()}
          isLoading={false}
          isFetching={false}
          error={null}
          onRetry={() => undefined}
        />
      </MemoryRouter>,
    );

    expect(
      screen.getByText("Cumulative performance vs benchmark"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Portfolio summary"),
    ).toBeInTheDocument();

    const keyMetrics = screen.getByRole("region", {
      name: "Portfolio report key metrics",
    });

    for (const label of [
      "Portfolio value",
      "Cumulative return",
      "CAGR",
      "Sharpe ratio",
      "Annualized volatility",
    ]) {
      expect(within(keyMetrics).getByText(label)).toBeInTheDocument();
    }

    expect(
      screen.getByRole("heading", { name: "Risk metrics" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Top holdings" }),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText("$1,100.00").length,
    ).toBeGreaterThan(0);

    expect(
      await screen.findByTestId(
        "performance-chart",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "allocation-panel",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "holdings-panel",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "movers-panel",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "review-items-panel",
      ),
    ).toBeInTheDocument();
  });

  it("keeps stale data visible and explicitly labeled", async () => {
    const snapshot = snapshotFixture();

    snapshot.performance!.portfolio_data_quality =
      "STALE";

    render(
      <MemoryRouter initialEntries={["/portfolios/portfolio-1/dashboard?range=3Y&view=report"]}>
        <DashboardOverview
          snapshot={snapshot}
          isLoading={false}
          isFetching={false}
          error={null}
          onRetry={() => undefined}
        />
      </MemoryRouter>,
    );

    expect(
      screen.getByText("Stale data"),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "performance-chart",
      ),
    ).toBeInTheDocument();
  });

  it("shows module-local failure without collapsing the summary", () => {
    const snapshot = snapshotFixture();

    snapshot.performance = null;

    snapshot.modules =
      snapshot.modules.map((module) =>
        module.module === "PERFORMANCE"
          ? {
              ...module,
              status: "UNAVAILABLE",
              error_code:
                "PERFORMANCE_UNAVAILABLE",
              detail:
                "Performance history is incomplete.",
            }
          : module,
      );

    render(
      <MemoryRouter initialEntries={["/portfolios/portfolio-1/dashboard?range=3Y&view=report"]}>
        <DashboardOverview
          snapshot={snapshot}
          isLoading={false}
          isFetching={false}
          error={null}
          onRetry={() => undefined}
        />
      </MemoryRouter>,
    );

    expect(
      screen.getByText(
        "Performance unavailable",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Performance history is incomplete.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Portfolio summary"),
    ).toBeInTheDocument();
  });
});