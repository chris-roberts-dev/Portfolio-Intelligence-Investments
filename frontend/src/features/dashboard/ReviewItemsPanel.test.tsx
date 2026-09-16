import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type {
    DashboardReviewItem,
    DashboardReviewItemsResult,
} from "../../types/dashboard";
import { ReviewItemsPanel } from "./ReviewItemsPanel";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_A_ID = "00000000-0000-0000-0000-000000000011";
const ASSET_B_ID = "00000000-0000-0000-0000-000000000012";

function reviewItem(
  overrides: Partial<DashboardReviewItem> & Pick<DashboardReviewItem, "key">,
): DashboardReviewItem {
  const { drilldown, ...itemOverrides } = overrides;

  return {
    source: "DAILY_PERFORMANCE",
    severity: "WARNING",
    category: "MARKET_DATA",
    code: "STALE_PRICE_USED",
    message: "A stale market price was used for AAA.",
    ...itemOverrides,
    drilldown: {
      resource: "PERFORMANCE",
      portfolio_id: PORTFOLIO_ID,
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      asset_id: ASSET_A_ID,
      symbol: "AAA",
      observation_date: "2026-09-15",
      ...drilldown,
    },
  };
}

function reviewItemsFixture(): DashboardReviewItemsResult {
  return {
    counts: {
      total: 4,
      by_severity: [
        {
          key: "ERROR",
          count: 1,
        },
        {
          key: "WARNING",
          count: 2,
        },
        {
          key: "INFO",
          count: 1,
        },
      ],
      by_category: [
        {
          key: "MARKET_DATA",
          count: 2,
        },
        {
          key: "DATA_COVERAGE",
          count: 0,
        },
        {
          key: "PROVIDER",
          count: 1,
        },
        {
          key: "VALUATION",
          count: 0,
        },
        {
          key: "ANALYTICS",
          count: 1,
        },
      ],
    },
    filtered_count: 4,
    filters: {
      severity: null,
      category: null,
    },
    items: [
      reviewItem({
        key: "CURRENT_VALUATION:PRICE_PROVIDER_FAILED:AAA:2026-09-15",
        source: "CURRENT_VALUATION",
        severity: "ERROR",
        category: "PROVIDER",
        code: "PRICE_PROVIDER_FAILED",
        message: "The current price provider failed for AAA.",
        drilldown: {
          resource: "HOLDINGS",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: ASSET_A_ID,
          symbol: "AAA",
          observation_date: "2026-09-15",
        },
      }),
      reviewItem({
        key: "DAILY_PERFORMANCE:STALE_PRICE_USED:AAA:2026-09-14",
        source: "DAILY_PERFORMANCE",
        severity: "WARNING",
        category: "MARKET_DATA",
        code: "STALE_PRICE_USED",
        message: "A stale market price was used for AAA on September 14.",
        drilldown: {
          resource: "PERFORMANCE",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: ASSET_A_ID,
          symbol: "AAA",
          observation_date: "2026-09-14",
        },
      }),
      reviewItem({
        key: "DAILY_PERFORMANCE:STALE_PRICE_USED:BBB:2026-09-15",
        source: "DAILY_PERFORMANCE",
        severity: "WARNING",
        category: "MARKET_DATA",
        code: "STALE_PRICE_USED",
        message: "A stale market price was used for BBB on September 15.",
        drilldown: {
          resource: "PERFORMANCE",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: ASSET_B_ID,
          symbol: "BBB",
          observation_date: "2026-09-15",
        },
      }),
      reviewItem({
        key: "ANALYTICS:INSUFFICIENT_HISTORY:PORTFOLIO:2026-09-15",
        source: "ANALYTICS",
        severity: "INFO",
        category: "ANALYTICS",
        code: "INSUFFICIENT_HISTORY",
        message:
          "Some analytics are unavailable because the selected period has insufficient history.",
        drilldown: {
          resource: "ANALYTICS",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: null,
          symbol: null,
          observation_date: "2026-09-15",
        },
      }),
    ],
    provenance: {
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      current_data_as_of: "2026-09-15T21:55:00Z",
      historical_data_as_of: "2026-09-15T21:50:00Z",
      analytics_as_of_date: "2026-09-15",
      calculated_at: "2026-09-15T22:00:00Z",
      engine_version: "0.1.0.dev0",
      included_sources: [
        "CURRENT_VALUATION",
        "DAILY_PERFORMANCE",
        "ANALYTICS",
      ],
      ordering_rule:
        "SEVERITY_THEN_CATEGORY_THEN_CODE_THEN_SYMBOL_DATE_V1",
    },
  };
}

function renderReviewItems(
  result: DashboardReviewItemsResult | null = reviewItemsFixture(),
  {
    isSnapshotComplete = true,
    moduleError = null,
  }: {
    isSnapshotComplete?: boolean;
    moduleError?: string | null;
  } = {},
) {
  render(
    <MemoryRouter
      initialEntries={[
        `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
      ]}
    >
      <ReviewItemsPanel
        reviewItems={result}
        isSnapshotComplete={isSnapshotComplete}
        moduleError={moduleError}
      />
    </MemoryRouter>,
  );
}

describe("ReviewItemsPanel", () => {
  it("renders stable server severity and category counts including zero buckets", () => {
    renderReviewItems();

    const errorFilter = screen.getByRole("button", {
      name: /^Error/i,
    });
    const warningFilter = screen.getByRole("button", {
      name: /^Warning/i,
    });
    const infoFilter = screen.getByRole("button", {
      name: /^Info/i,
    });

    expect(errorFilter).toHaveTextContent("1");
    expect(warningFilter).toHaveTextContent("2");
    expect(infoFilter).toHaveTextContent("1");

    const marketDataFilter = screen.getByRole("button", {
      name: /^Market data/i,
    });
    const dataCoverageFilter = screen.getByRole("button", {
      name: /^Data coverage/i,
    });
    const providerFilter = screen.getByRole("button", {
      name: /^Provider/i,
    });
    const valuationFilter = screen.getByRole("button", {
      name: /^Valuation/i,
    });
    const analyticsFilter = screen.getByRole("button", {
      name: /^Analytics/i,
    });

    expect(marketDataFilter).toHaveTextContent("2");
    expect(dataCoverageFilter).toHaveTextContent("0");
    expect(providerFilter).toHaveTextContent("1");
    expect(valuationFilter).toHaveTextContent("0");
    expect(analyticsFilter).toHaveTextContent("1");

    expect(screen.getByText("4 review items")).toBeInTheDocument();
  });

  it("preserves canonical server item order", () => {
    renderReviewItems();

    const items = screen.getAllByTestId("review-item");

    expect(items).toHaveLength(4);

    expect(items[0]).toHaveAttribute(
      "data-review-item-key",
      "CURRENT_VALUATION:PRICE_PROVIDER_FAILED:AAA:2026-09-15",
    );
    expect(items[1]).toHaveAttribute(
      "data-review-item-key",
      "DAILY_PERFORMANCE:STALE_PRICE_USED:AAA:2026-09-14",
    );
    expect(items[2]).toHaveAttribute(
      "data-review-item-key",
      "DAILY_PERFORMANCE:STALE_PRICE_USED:BBB:2026-09-15",
    );
    expect(items[3]).toHaveAttribute(
      "data-review-item-key",
      "ANALYTICS:INSUFFICIENT_HISTORY:PORTFOLIO:2026-09-15",
    );
  });

  it("filters details without changing server counts or re-ranking matches", () => {
    renderReviewItems();

    const warningFilter = screen.getByRole("button", {
      name: /^Warning/i,
    });

    expect(warningFilter).toHaveTextContent("2");

    fireEvent.click(warningFilter);

    const items = screen.getAllByTestId("review-item");

    expect(items).toHaveLength(2);

    expect(
      within(items[0]!).getByText(
        "A stale market price was used for AAA on September 14.",
      ),
    ).toBeInTheDocument();

    expect(
      within(items[1]!).getByText(
        "A stale market price was used for BBB on September 15.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Showing 2 of 4 server-provided review items."),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: /^Error/i,
      }),
    ).toHaveTextContent("1");

    expect(
      screen.getByRole("button", {
        name: /^Warning/i,
      }),
    ).toHaveTextContent("2");

    expect(
      screen.getByRole("button", {
        name: /^Info/i,
      }),
    ).toHaveTextContent("1");
  });

  it("supports accessible severity and category filter state", () => {
    renderReviewItems();

    const allSeverities = screen.getByRole("button", {
      name: /^All severities/i,
    });
    const warning = screen.getByRole("button", {
      name: /^Warning/i,
    });
    const analytics = screen.getByRole("button", {
      name: /^Analytics/i,
    });

    expect(allSeverities).toHaveTextContent("4");
    expect(allSeverities).toHaveAttribute("aria-pressed", "true");
    expect(warning).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(warning);

    expect(allSeverities).toHaveAttribute("aria-pressed", "false");
    expect(warning).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(analytics);

    expect(analytics).toHaveAttribute("aria-pressed", "true");

    expect(
      screen.getByRole("button", {
        name: "Clear review filters",
      }),
    ).toBeInTheDocument();
  });

  it("preserves dashboard range context in native holding drill-down links", () => {
    renderReviewItems();

    const link = screen.getByRole("link", {
      name: "Open holding",
    });

    expect(link).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/holdings/${ASSET_A_ID}?range=6M`,
    );
  });

  it("renders performance and analytics drill-down context without inventing routes", () => {
    renderReviewItems();

    const items = screen.getAllByTestId("review-item");

    const performanceItem = items[1]!;
    const analyticsItem = items[3]!;

    expect(performanceItem).toHaveTextContent("Performance");
    expect(analyticsItem).toHaveTextContent("Analytics");

    expect(
      within(analyticsItem).getByText("Portfolio-level review item"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByRole("link", {
        name: "Open holding",
      }),
    ).toHaveLength(1);
  });

  it("renders owner-scoped requested period, observation, symbol, and asset context", () => {
    renderReviewItems();

    const firstItem = screen.getAllByTestId("review-item")[0]!;

    expect(firstItem).toHaveTextContent("Holdings");
    expect(firstItem).toHaveTextContent(
      "2026-09-01 to 2026-09-16 (end exclusive)",
    );
    expect(firstItem).toHaveTextContent("2026-09-15");
    expect(firstItem).toHaveTextContent("AAA");
    expect(firstItem).toHaveTextContent(PORTFOLIO_ID);
    expect(firstItem).toHaveTextContent(ASSET_A_ID);
  });

  it("renders calculation and data-as-of provenance without frontend recomputation", () => {
    renderReviewItems();

    expect(screen.getByText(/Requested period:/)).toHaveTextContent(
      "2026-09-01 to 2026-09-16",
    );

    expect(screen.getByText(/Current data as of/)).toBeInTheDocument();
    expect(screen.getByText(/Historical data as of/)).toBeInTheDocument();
    expect(screen.getByText(/Analytics as of/)).toBeInTheDocument();

    expect(screen.getByText(/Provider: mock/)).toBeInTheDocument();
    expect(screen.getByText(/Engine: 0.1.0.dev0/)).toBeInTheDocument();
    expect(screen.getByText(/Base currency: USD/)).toBeInTheDocument();

    expect(
      screen.getByText(
        /Current valuation · Daily performance · Analytics/,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "SEVERITY_THEN_CATEGORY_THEN_CODE_THEN_SYMBOL_DATE_V1",
      ),
    ).toBeInTheDocument();
  });

  it("shows an explicit empty state when the server reports zero review items", () => {
    const result = reviewItemsFixture();

    result.counts = {
      total: 0,
      by_severity: [
        { key: "ERROR", count: 0 },
        { key: "WARNING", count: 0 },
        { key: "INFO", count: 0 },
      ],
      by_category: [
        { key: "MARKET_DATA", count: 0 },
        { key: "DATA_COVERAGE", count: 0 },
        { key: "PROVIDER", count: 0 },
        { key: "VALUATION", count: 0 },
        { key: "ANALYTICS", count: 0 },
      ],
    };
    result.filtered_count = 0;
    result.items = [];

    renderReviewItems(result);

    expect(screen.getByText("No review items")).toBeInTheDocument();

    expect(
      screen.getByText(
        "The current valuation, daily performance, and analytics sources reported no supported data-quality conditions for this selected period.",
      ),
    ).toBeInTheDocument();
  });

  it("shows an explicit no-matches state for a filter combination", () => {
    renderReviewItems();

    fireEvent.click(
      screen.getByRole("button", {
        name: /^Error/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: /^Analytics/i,
      }),
    );

    expect(
      screen.getByText("No matching review items"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "No server-provided review items match the selected severity and category filters.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Showing 0 of 4 server-provided review items."),
    ).toBeInTheDocument();
  });

  it("clears active filters and restores canonical server detail order", () => {
    renderReviewItems();

    const warningFilter = screen.getByRole("button", {
      name: /^Warning/i,
    });

    expect(warningFilter).toHaveTextContent("2");

    fireEvent.click(warningFilter);

    expect(screen.getAllByTestId("review-item")).toHaveLength(2);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Clear review filters",
      }),
    );

    const items = screen.getAllByTestId("review-item");

    expect(items).toHaveLength(4);

    expect(items[0]).toHaveAttribute(
      "data-review-item-key",
      "CURRENT_VALUATION:PRICE_PROVIDER_FAILED:AAA:2026-09-15",
    );

    expect(items[3]).toHaveAttribute(
      "data-review-item-key",
      "ANALYTICS:INSUFFICIENT_HISTORY:PORTFOLIO:2026-09-15",
    );
  });

  it("keeps available review items visible while labeling a partial dashboard snapshot", () => {
    renderReviewItems(reviewItemsFixture(), {
      isSnapshotComplete: false,
    });

    expect(screen.getByText("Partial snapshot")).toBeInTheDocument();

    expect(
      screen.getByText(
        "This dashboard snapshot is partial because another module is unavailable. The review-item module below remains available with its own calculation and data provenance.",
      ),
    ).toBeInTheDocument();

    expect(screen.getAllByTestId("review-item")).toHaveLength(4);
  });

  it("shows a module-local unavailable state", () => {
    renderReviewItems(null, {
      moduleError:
        "Review items require current valuation, daily performance, and analytics from the shared snapshot context.",
    });

    expect(
      screen.getByText("Review items unavailable"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Review items require current valuation, daily performance, and analytics from the shared snapshot context.",
      ),
    ).toBeInTheDocument();
  });

  it("shows an explicit unavailable state when the module result is null", () => {
    renderReviewItems(null);

    expect(
      screen.getByText("Review items unavailable"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "No data-quality review-item module is available for this dashboard snapshot.",
      ),
    ).toBeInTheDocument();
  });

  it("does not expose unsupported speculative alert categories", () => {
    renderReviewItems();

    expect(screen.queryByText(/account sync/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/classification/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/corporate action/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/allocation drift/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/concentration threshold/i),
    ).not.toBeInTheDocument();
  });
});