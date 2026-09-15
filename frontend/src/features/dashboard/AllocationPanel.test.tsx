import { render, screen } from "@testing-library/react";

import type { DashboardAllocationResult } from "../../types/dashboard";
import { AllocationPanel } from "./AllocationPanel";

vi.mock("../../components/charts/AllocationChart", () => ({
  AllocationChart: () => <div data-testid="allocation-chart">Allocation chart</div>,
}));

function allocationFixture(): DashboardAllocationResult {
  return {
    allocation_available: true,
    groups: [
      {
        key: "STOCK",
        label: "Stocks",
        is_cash: false,
        asset_count: 2,
        market_value: "600.00",
        weight: 0.6,
      },
      {
        key: "ETF",
        label: "ETFs",
        is_cash: false,
        asset_count: 1,
        market_value: "300.00",
        weight: 0.3,
      },
      {
        key: "CASH",
        label: "Cash",
        is_cash: true,
        asset_count: 0,
        market_value: "100.00",
        weight: 0.1,
      },
    ],
    totals: {
      total_market_value: "1000.00",
      invested_value: "900.00",
      cash_value: "100.00",
      invested_weight: 0.9,
      cash_weight: 0.1,
    },
    data_quality: "CURRENT",
    unavailable_reason: null,
    warnings: [],
    provenance: {
      portfolio_id: "00000000-0000-0000-0000-000000000002",
      base_currency: "USD",
      provider: "mock",
      as_of: "2026-09-15T22:00:00Z",
      data_as_of: "2026-09-15T21:55:00Z",
      calculated_at: "2026-09-15T22:00:00Z",
      price_field: "close",
      grouping_dimension: "ASSET_CLASS",
      supported_grouping_dimensions: ["ASSET_CLASS"],
      grouping_source: "Asset.asset_type",
      ordering_rule: "SECURITY_WEIGHT_DESC_THEN_GROUP_KEY_CASH_LAST_V1",
      other_grouping_applied: false,
      other_grouping_threshold: null,
      other_grouping_rule:
        "No Other aggregation is applied in the MVP because persisted security asset types are exhaustively constrained to STOCK and ETF.",
      weight_sum_tolerance: 1e-8,
    },
  };
}

describe("AllocationPanel", () => {
  it("renders backend-authoritative groups, exact values, and equivalent table data", async () => {
    render(
      <AllocationPanel
        allocation={allocationFixture()}
        currency="USD"
        moduleError={null}
      />,
    );

    expect(screen.getByRole("heading", { name: "Allocation" })).toBeInTheDocument();
    expect(screen.getByText("$900.00")).toBeInTheDocument();
    expect(screen.getAllByText("$100.00").length).toBeGreaterThan(0);
    expect(screen.getByRole("rowheader", { name: "Stocks" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "ETFs" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Cash" })).toBeInTheDocument();
    expect(screen.getByText("60.0%")).toBeInTheDocument();
    expect(screen.getByText("30.0%")).toBeInTheDocument();
    expect(screen.getByText("10.0%")).toBeInTheDocument();
    expect(
      await screen.findByTestId("allocation-chart"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No Other aggregation is applied in the MVP/),
    ).toBeInTheDocument();
  });

  it("keeps stale allocation visible and explicitly labeled", () => {
    const allocation = allocationFixture();
    allocation.data_quality = "STALE";

    render(
      <AllocationPanel
        allocation={allocation}
        currency="USD"
        moduleError={null}
      />,
    );

    expect(screen.getByText("Stale data")).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Stocks" })).toBeInTheDocument();
  });

  it("shows explicit unavailable state without fabricating weights", () => {
    const allocation = allocationFixture();
    allocation.allocation_available = false;
    allocation.data_quality = "PARTIAL";
    allocation.unavailable_reason = "CURRENT_VALUATION_INCOMPLETE";
    allocation.groups = [];
    allocation.totals.total_market_value = null;
    allocation.totals.invested_value = null;
    allocation.totals.invested_weight = null;
    allocation.totals.cash_weight = null;

    render(
      <AllocationPanel
        allocation={allocation}
        currency="USD"
        moduleError={null}
      />,
    );

    expect(screen.getByText("Partial data")).toBeInTheDocument();
    expect(screen.getByText("Allocation weights are not available.")).toBeInTheDocument();
    expect(screen.getByText("Current valuation incomplete")).toBeInTheDocument();
    expect(screen.queryByTestId("allocation-chart")).not.toBeInTheDocument();
  });
});
