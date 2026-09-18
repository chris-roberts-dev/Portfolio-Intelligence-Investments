import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { DashboardHoldingsResult } from "../../types/dashboard";
import { PortfolioReportTopHoldings } from "./PortfolioReportTopHoldings";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_ID = "00000000-0000-0000-0000-000000000011";

function holdingsFixture(): DashboardHoldingsResult {
  return {
    holdings: [
      {
        asset_id: ASSET_ID,
        symbol: "AAA",
        name: "AAA Incorporated",
        asset_type: "STOCK",
        currency: "USD",
        quantity: "10.000000000000",
        current_price: "100.00",
        current_price_date: "2026-09-18",
        current_price_retrieved_at: "2026-09-18T20:00:00Z",
        stale_trading_sessions: 0,
        market_value: "1000.00",
        weight: 0.6,
        weight_unavailable_reason: null,
        selected_period_return: 0.12,
        selected_period_return_unavailable_reason: null,
        contribution_to_return: 0.07,
        contribution_unavailable_reason: null,
        sparkline: [],
        data_quality: "CURRENT",
        warnings: [],
      },
    ],
    data_quality: "CURRENT",
    warnings: [],
    provenance: {
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-06-18",
      requested_end_exclusive: "2026-09-19",
      effective_start: "2026-06-18",
      effective_end_exclusive: "2026-09-19",
      current_price_as_of: "2026-09-18T20:00:00Z",
      period_data_as_of: "2026-09-18T20:00:00Z",
      calculated_at: "2026-09-18T20:05:00Z",
      current_price_field: "close",
      period_price_field: "adjusted_close",
    },
  };
}

describe("PortfolioReportTopHoldings", () => {
  it("links a report security to canonical holding research while preserving report context", () => {
    render(
      <MemoryRouter
        initialEntries={[
          `/portfolios/${PORTFOLIO_ID}/dashboard?range=3Y&view=report`,
        ]}
      >
        <PortfolioReportTopHoldings holdings={holdingsFixture()} currency="USD" />
      </MemoryRouter>,
    );

    const researchLink = screen.getByRole("link", {
      name: "Research AAA holding",
    });

    expect(researchLink).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/holdings/${ASSET_ID}?range=3Y&view=report`,
    );

    researchLink.focus();
    expect(researchLink).toHaveFocus();
  });
});
