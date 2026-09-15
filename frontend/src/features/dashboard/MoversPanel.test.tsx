import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { MoversPanel } from "./MoversPanel";
import type {
  DashboardMover,
  DashboardMoversResult,
} from "../../types/dashboard";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function mover(
  assetId: string,
  symbol: string,
  selectedPeriodReturn: number,
  contribution: number,
  isCurrentHolding = true,
): DashboardMover {
  return {
    asset_id: assetId,
    symbol,
    name: `${symbol} Incorporated`,
    asset_type: "STOCK",
    currency: "USD",
    is_current_holding: isCurrentHolding,
    quantity: isCurrentHolding ? "10.000000000000" : null,
    current_price: isCurrentHolding ? "100.00000000" : null,
    current_price_date: isCurrentHolding ? "2026-09-15" : null,
    current_price_retrieved_at: isCurrentHolding
      ? "2026-09-15T21:55:00Z"
      : null,
    stale_trading_sessions: isCurrentHolding ? 0 : null,
    market_value: isCurrentHolding ? "1000.00000000" : null,
    weight: isCurrentHolding ? 0.5 : null,
    selected_period_return: selectedPeriodReturn,
    contribution_to_return: contribution,
    sparkline: [],
    data_quality: "CURRENT",
    unavailable_reasons: isCurrentHolding ? [] : ["NOT_CURRENT_HOLDING"],
  };
}

function moversFixture(): DashboardMoversResult {
  const aaa = mover(
    "00000000-0000-0000-0000-000000000011",
    "AAA",
    0.15,
    0.06,
  );
  const bbb = mover(
    "00000000-0000-0000-0000-000000000012",
    "BBB",
    0.12,
    0.04,
  );
  const ccc = mover(
    "00000000-0000-0000-0000-000000000013",
    "CCC",
    -0.08,
    -0.03,
  );
  const sold = mover(
    "00000000-0000-0000-0000-000000000014",
    "SOLD",
    -0.04,
    0.02,
    false,
  );

  return {
    top_gainers: [aaa, bbb],
    top_losers: [ccc, sold],
    largest_contributors: [aaa, bbb, sold],
    largest_detractors: [ccc],
    reconciliation: {
      status: "AVAILABLE",
      periods: 10,
      cumulative_return: 0.09,
      asset_contribution_total: 0.09,
      unattributed_contribution: 0.001,
      reconciliation_error: 0,
      unavailable_reason: null,
    },
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
      attribution_method: "ASSET_PNL_WEALTH_LINKED_V1",
      engine_version: "0.1.0.dev0",
    },
  };
}

function renderMovers(result = moversFixture()) {
  render(
    <MemoryRouter
      initialEntries={[`/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`]}
    >
      <MoversPanel
        movers={result}
        portfolioId={PORTFOLIO_ID}
        moduleError={null}
      />
    </MemoryRouter>,
  );
}

describe("MoversPanel", () => {
  it("renders server-provided ranking order without client re-sorting", () => {
    renderMovers();

    const cards = screen.getAllByTestId("mover-card");
    expect(within(cards[0]!).getByText("AAA")).toBeInTheDocument();
    expect(within(cards[1]!).getByText("BBB")).toBeInTheDocument();
  });

  it("switches ranking tabs with keyboard navigation", () => {
    renderMovers();

    const gainers = screen.getByRole("tab", { name: "Top Gainers" });
    fireEvent.keyDown(gainers, { key: "ArrowRight" });

    const losers = screen.getByRole("tab", { name: "Top Losers" });
    expect(losers).toHaveAttribute("aria-selected", "true");
    expect(losers).toHaveFocus();
    expect(screen.getByText("CCC")).toBeInTheDocument();
  });


  it("preserves contributor order and keeps sold historical positions visible", () => {
    renderMovers();

    fireEvent.click(
      screen.getByRole("tab", { name: "Largest Contributors" }),
    );

    const cards = screen.getAllByTestId("mover-card");
    expect(within(cards[0]!).getByText("AAA")).toBeInTheDocument();
    expect(within(cards[1]!).getByText("BBB")).toBeInTheDocument();
    expect(within(cards[2]!).getByText("SOLD")).toBeInTheDocument();
    expect(
      within(cards[2]!).getByText("Historical position"),
    ).toBeInTheDocument();
  });

  it("preserves portfolio range context in mover detail links", () => {
    renderMovers();

    expect(
      screen.getByRole("link", { name: "Open AAA holding details" }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/holdings/00000000-0000-0000-0000-000000000011?range=6M`,
    );
  });

  it("renders backend reconciliation and unattributed contribution metadata", () => {
    renderMovers();

    expect(screen.getByText("Reconciled")).toBeInTheDocument();
    expect(screen.getByText("Unattributed")).toBeInTheDocument();
    expect(screen.getByText("+0.10%")).toBeInTheDocument();
    expect(screen.getByText("Reconciliation error")).toBeInTheDocument();
  });


  it("shows a module-local unavailable state", () => {
    render(
      <MemoryRouter>
        <MoversPanel
          movers={null}
          portfolioId={PORTFOLIO_ID}
          moduleError="Mover attribution inputs are unavailable."
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Movers unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("Mover attribution inputs are unavailable."),
    ).toBeInTheDocument();
  });

  it("shows explicit attribution unavailability without fabricating values", () => {
    const result = moversFixture();
    result.reconciliation = {
      status: "UNAVAILABLE",
      periods: 0,
      cumulative_return: null,
      asset_contribution_total: null,
      unattributed_contribution: null,
      reconciliation_error: null,
      unavailable_reason: "PORTFOLIO_TWR_UNAVAILABLE",
    };
    result.data_quality = "PARTIAL";

    renderMovers(result);

    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Portfolio twr unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
  });
});
