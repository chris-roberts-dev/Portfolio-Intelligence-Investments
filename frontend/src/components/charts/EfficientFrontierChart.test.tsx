import { render, screen, within } from "@testing-library/react";

import { EfficientFrontierChart } from "./EfficientFrontierChart";

vi.mock("echarts/core", () => ({
  use: vi.fn(),
}));
vi.mock("echarts/charts", () => ({
  ScatterChart: {},
}));
vi.mock("echarts/components", () => ({
  AriaComponent: {},
  GridComponent: {},
  TooltipComponent: {},
}));
vi.mock("echarts/renderers", () => ({
  CanvasRenderer: {},
}));
vi.mock("./useECharts", () => ({
  useECharts: vi.fn(),
}));

describe("EfficientFrontierChart", () => {
  it("renders every server frontier point in an accessible table without adding points", () => {
    render(
      <EfficientFrontierChart
        assetLabels={new Map([
          ["asset-a", "AAPL · Apple Inc."],
          ["asset-b", "MSFT · Microsoft Corp."],
        ])}
        points={[
          {
            method: "EFFICIENT_FRONTIER",
            weights: [
              { asset_id: "asset-a", weight: 0.3 },
              { asset_id: "asset-b", weight: 0.7 },
            ],
            expected_return: 0.1,
            expected_volatility: 0.12,
            sharpe_ratio: 0.83,
            target_return: 0.1,
          },
          {
            method: "EFFICIENT_FRONTIER",
            weights: [
              { asset_id: "asset-a", weight: 0.5 },
              { asset_id: "asset-b", weight: 0.5 },
            ],
            expected_return: 0.14,
            expected_volatility: 0.18,
            sharpe_ratio: 0.78,
            target_return: 0.14,
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("img", {
        name: "Efficient frontier expected return and volatility chart",
      }),
    ).toBeInTheDocument();

    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[1]!).getAllByText("10.00%")).toHaveLength(2);
    expect(within(rows[1]!).getByText("12.00%")).toBeInTheDocument();
    expect(within(rows[2]!).getAllByText("14.00%")).toHaveLength(2);
    expect(within(rows[2]!).getByText("18.00%")).toBeInTheDocument();
    expect(
      within(rows[1]!).getByText(/AAPL · Apple Inc\.: 30\.00%/),
    ).toBeInTheDocument();
  });
});
