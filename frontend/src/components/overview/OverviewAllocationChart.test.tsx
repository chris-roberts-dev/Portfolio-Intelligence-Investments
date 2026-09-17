import { render, screen, within } from "@testing-library/react";

import { OverviewAllocationChart } from "./OverviewAllocationChart";

vi.mock("../charts/useECharts", () => ({
  useECharts: vi.fn(),
}));

describe("OverviewAllocationChart", () => {
  it("provides an accessible table for the authoritative allocation groups", () => {
    render(
      <OverviewAllocationChart
        groups={[
          {
            key: "stock",
            label: "Stocks",
            is_cash: false,
            asset_count: 3,
            market_value: "95000.00",
            weight: 0.95,
          },
          {
            key: "cash",
            label: "Cash",
            is_cash: true,
            asset_count: 0,
            market_value: "5000.00",
            weight: 0.05,
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("img", { name: "Current portfolio allocation chart" }),
    ).toBeInTheDocument();

    const table = screen.getByRole("table");
    expect(within(table).getByText("Stocks")).toBeInTheDocument();
    expect(within(table).getByText("Cash")).toBeInTheDocument();
    expect(within(table).getByText("95.0%")).toBeInTheDocument();
    expect(within(table).getByText("5.0%")).toBeInTheDocument();
  });
});
