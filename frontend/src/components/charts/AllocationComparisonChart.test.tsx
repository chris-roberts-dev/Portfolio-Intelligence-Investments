import { render, screen, within } from "@testing-library/react";

import { AllocationComparisonChart } from "./AllocationComparisonChart";

vi.mock("echarts/core", () => ({
  use: vi.fn(),
}));
vi.mock("echarts/charts", () => ({
  BarChart: {},
}));
vi.mock("echarts/components", () => ({
  AriaComponent: {},
  GridComponent: {},
  LegendComponent: {},
  TooltipComponent: {},
}));
vi.mock("echarts/renderers", () => ({
  CanvasRenderer: {},
}));
vi.mock("./useECharts", () => ({
  useECharts: vi.fn(),
}));

describe("AllocationComparisonChart", () => {
  it("keeps unavailable optimization values explicit instead of deriving them", () => {
    render(
      <AllocationComparisonChart
        baselineLabel="Custom baseline"
        rows={[
          {
            assetId: "asset-a",
            label: "AAPL",
            currentWeight: 0.4,
            equalWeight: 0.5,
            minimumVarianceWeight: null,
            maximumSharpeWeight: null,
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("img", {
        name: "Custom baseline and optimized allocation comparison chart",
      }),
    ).toBeInTheDocument();

    const row = within(screen.getByRole("table")).getAllByRole("row")[1]!;
    expect(within(row).getByText("40.00%")).toBeInTheDocument();
    expect(within(row).getByText("50.00%")).toBeInTheDocument();
    expect(within(row).getAllByText("Not available")).toHaveLength(2);
  });
});