import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { HoldingsPanel } from "./HoldingsPanel";
import type {
  DashboardHolding,
  DashboardHoldingsResult,
} from "../../types/dashboard";

vi.mock("../../components/charts/HoldingSparkline", () => ({
  HoldingSparkline: ({ symbol }: { symbol: string }) => (
    <div data-testid={`sparkline-${symbol}`}>Sparkline</div>
  ),
}));

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function holding(
  assetId: string,
  symbol: string,
  marketValue: string,
  weight: number,
  selectedReturn: number,
): DashboardHolding {
  return {
    asset_id: assetId,
    symbol,
    name: `${symbol} Incorporated`,
    asset_type: "STOCK",
    currency: "USD",
    quantity: "10.00000000",
    current_price: "100.00",
    current_price_date: "2026-09-15",
    current_price_retrieved_at: "2026-09-15T21:55:00Z",
    stale_trading_sessions: 0,
    market_value: marketValue,
    weight,
    weight_unavailable_reason: null,
    selected_period_return: selectedReturn,
    selected_period_return_unavailable_reason: null,
    contribution_to_return: null,
    contribution_unavailable_reason: "CONTRIBUTION_NOT_CALCULATED",
    sparkline: [
      {
        observation_date: "2026-09-01",
        adjusted_close: "90.00",
      },
      {
        observation_date: "2026-09-02",
        adjusted_close: null,
      },
      {
        observation_date: "2026-09-15",
        adjusted_close: "100.00",
      },
    ],
    data_quality: "CURRENT",
    warnings: [],
  };
}

function holdingsFixture(): DashboardHoldingsResult {
  return {
    holdings: [
      holding(
        "00000000-0000-0000-0000-000000000011",
        "AAA",
        "100.00",
        0.1,
        0.05,
      ),
      holding(
        "00000000-0000-0000-0000-000000000012",
        "BBB",
        "900.00",
        0.9,
        -0.02,
      ),
    ],
    data_quality: "CURRENT",
    warnings: [],
    provenance: {
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      current_price_as_of: "2026-09-15T21:55:00Z",
      period_data_as_of: "2026-09-15T21:55:00Z",
      calculated_at: "2026-09-15T22:00:00Z",
      current_price_field: "close",
      period_price_field: "adjusted_close",
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter
      initialEntries={[
        `/portfolios/${PORTFOLIO_ID}/dashboard?range=3M`,
      ]}
    >
      <HoldingsPanel
        holdings={holdingsFixture()}
        currency="USD"
        portfolioId={PORTFOLIO_ID}
        moduleError={null}
      />
    </MemoryRouter>,
  );
}

function holdingLinks(): HTMLAnchorElement[] {
  return screen.getAllByRole("link", {
    name: /Open .* holding details/,
  }) as HTMLAnchorElement[];
}

describe("HoldingsPanel", () => {
  it("sorts deterministically by market value and preserves route context", () => {
    renderPanel();

    const links = holdingLinks();

    expect(links[0]).toHaveAccessibleName("Open BBB holding details");
    expect(links[1]).toHaveAccessibleName("Open AAA holding details");
    expect(links[0]?.getAttribute("href")).toBe(
      `/portfolios/${PORTFOLIO_ID}/holdings/00000000-0000-0000-0000-000000000012?range=3M`,
    );
    expect(screen.getByTestId("sparkline-BBB")).toBeInTheDocument();
  });

  it("supports keyboard-accessible native links and deterministic symbol sorting", () => {
    renderPanel();

    fireEvent.change(screen.getByRole("combobox", { name: "Sort holdings by" }), {
      target: { value: "SYMBOL" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Sort holdings ascending" }),
    );

    const links = holdingLinks();

    expect(links[0]).toHaveAccessibleName("Open AAA holding details");
    links[0]?.focus();
    expect(links[0]).toHaveFocus();
  });

  it("uses text and directional symbols in addition to semantic colors", () => {
    renderPanel();

    expect(screen.getByText("▲ +5.00%")).toBeInTheDocument();
    expect(screen.getByText("▼ -2.00%")).toBeInTheDocument();
  });
});
