import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import type { PortfolioAnalyticsResult } from "../types/analytics";
import { PortfolioAnalysisPage } from "./PortfolioAnalysisPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        retryDelay: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
    },
  });

  return queryClient;
}

function portfolioListResponse(): Response {
  return new Response(
    JSON.stringify([
      {
        id: PORTFOLIO_ID,
        name: "Primary portfolio",
        base_currency: "USD",
        benchmark_asset_id: "00000000-0000-0000-0000-000000000090",
        created_at: "2025-01-02T15:00:00Z",
        updated_at: "2026-09-15T22:00:00Z",
      },
    ]),
    {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    },
  );
}

function analyticsFixture(): PortfolioAnalyticsResult {
  return {
    portfolio_id: PORTFOLIO_ID,
    observations: 42,
    benchmark_observations: 40,
    cumulative_return: 0.125,
    cagr: {
      value: 0.14,
      wealth_ratio: 1.125,
      elapsed_days: 300,
      elapsed_years: 0.821,
      is_short_period: true,
    },
    annualized_volatility: 0.18,
    sharpe: {
      value: 0.78,
      observations: 42,
      risk_free_rate_annual: 0,
      risk_free_rate_daily: 0,
      annualization_factor: 252,
      warnings: [],
    },
    sortino: {
      value: 1.12,
      observations: 42,
      minimum_acceptable_return_annual: 0,
      minimum_acceptable_return_daily: 0,
      downside_deviation: 0.11,
      annualization_factor: 252,
      warnings: [],
    },
    maximum_drawdown: {
      value: -0.09,
      observations: 42,
      peak_index: 12,
      trough_index: 18,
      warnings: [],
    },
    beta: {
      value: 0.91,
      observations: 40,
      warnings: [],
    },
    benchmark_correlation: {
      value: 0.98,
      observations: 40,
      warnings: [],
    },
    current_allocation: {
      positions: [
        {
          asset_id: "00000000-0000-0000-0000-000000000011",
          market_value: 900,
          weight: 0.9,
        },
      ],
      cash_value: 100,
      cash_weight: 0.1,
      total_market_value: 1000,
      weight_sum: 1,
      weight_sum_tolerance: 1e-8,
    },
    concentration: {
      largest_position_weight: 0.9,
      herfindahl_hirschman_index: 0.81,
      security_position_count: 1,
      cash_weight: 0.1,
      largest_position_includes_cash: false,
      hhi_includes_cash: false,
      long_only: true,
      weight_sum_tolerance: 1e-8,
    },
    rolling_return_window: null,
    rolling_returns: [],
    provenance: {
      engine_version: "0.1.0.dev0",
      as_of_date: "2026-09-15",
      period_start: "2026-08-01",
      period_end: "2026-09-15",
      data_source: "mock",
      price_field: "adjusted_close",
      annualization_factor: 252,
      benchmark: "SPY",
      assumptions: [
        "historical returns use adjusted_close",
        "current allocation uses raw close",
        "benchmark correlation uses Pearson correlation on exact date intersections",
        "risk_free_rate_annual=0.0",
        "minimum_acceptable_return_annual=0.0",
      ],
      warnings: [],
    },
    warnings: [],
  };
}

function analyticsFixtureWithRolling(): PortfolioAnalyticsResult {
  const analytics = analyticsFixture();

  analytics.rolling_return_window = 20;
  analytics.rolling_returns = [
    {
      period_end: "2026-09-10",
      value: 0.035,
    },
    {
      period_end: "2026-09-15",
      value: 0.045,
    },
  ];
  analytics.provenance.assumptions.push(
    "rolling_return_window_observations=20",
  );

  return analytics;
}

function renderPage(
  initialEntry = `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
) {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/portfolios/:portfolioId/analysis"
            element={<PortfolioAnalysisPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function installSuccessfulFetch(
  analytics = analyticsFixture(),
) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/v1/portfolios/")) {
        return portfolioListResponse();
      }

      if (
        url.includes(
          `/api/v1/analytics/portfolios/${PORTFOLIO_ID}/`,
        )
      ) {
        return new Response(JSON.stringify(analytics), {
          status: 200,
          headers: {
            "content-type": "application/json",
          },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    },
  );

  vi.stubGlobal("fetch", fetchMock);

  return fetchMock;
}

function installAnalyticsError(
  status: number,
  payload: {
    code: string;
    detail: string;
  },
) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/v1/portfolios/")) {
        return portfolioListResponse();
      }

      if (
        url.includes(
          `/api/v1/analytics/portfolios/${PORTFOLIO_ID}/`,
        )
      ) {
        return new Response(JSON.stringify(payload), {
          status,
          headers: {
            "content-type": "application/json",
          },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PortfolioAnalysisPage", () => {
  it("uses the explicit PortfolioAnalyticsResult transport contract", () => {
    const analytics = analyticsFixture();

    expectTypeOf(analytics).toMatchTypeOf<PortfolioAnalyticsResult>();

    expectTypeOf<
      PortfolioAnalyticsResult["cumulative_return"]
    >().toEqualTypeOf<number | null>();

    expectTypeOf<
      PortfolioAnalyticsResult["benchmark_observations"]
    >().toEqualTypeOf<number | null>();

    expectTypeOf<
      PortfolioAnalyticsResult["benchmark_correlation"]
    >().toMatchTypeOf<
      | {
          value: number | null;
          observations: number;
          warnings: { code: string; message: string }[];
        }
      | null
    >();

    expectTypeOf<
      PortfolioAnalyticsResult["rolling_return_window"]
    >().toEqualTypeOf<number | null>();
  });

  it("renders backend-provided analytics values without recomputing them", async () => {
    installSuccessfulFetch();
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Analytical results",
      }),
    ).toBeInTheDocument();

    const cumulativeReturn = screen
      .getByText("Cumulative return")
      .closest("article");
    const cagr = screen.getByText("CAGR").closest("article");
    const volatility = screen
      .getByText("Annualized volatility")
      .closest("article");
    const sharpe = screen
      .getByText("Sharpe ratio")
      .closest("article");
    const sortino = screen
      .getByText("Sortino ratio")
      .closest("article");
    const downside = screen
      .getByText("Downside deviation")
      .closest("article");
    const drawdown = screen
      .getByText("Maximum drawdown")
      .closest("article");
    const beta = screen.getByText("Beta").closest("article");

    expect(cumulativeReturn).not.toBeNull();
    expect(cagr).not.toBeNull();
    expect(volatility).not.toBeNull();
    expect(sharpe).not.toBeNull();
    expect(sortino).not.toBeNull();
    expect(downside).not.toBeNull();
    expect(drawdown).not.toBeNull();
    expect(beta).not.toBeNull();

    expect(
      within(cumulativeReturn!).getByText("+12.50%"),
    ).toBeInTheDocument();
    expect(within(cagr!).getByText("+14.00%")).toBeInTheDocument();
    expect(
      within(volatility!).getByText("18.00%"),
    ).toBeInTheDocument();
    expect(within(sharpe!).getByText("0.78")).toBeInTheDocument();
    expect(within(sortino!).getByText("1.12")).toBeInTheDocument();
    expect(
      within(downside!).getByText("11.00%"),
    ).toBeInTheDocument();
    expect(
      within(drawdown!).getByText("-9.00%"),
    ).toBeInTheDocument();
    expect(within(beta!).getByText("0.91")).toBeInTheDocument();

    expect(screen.getByText("$1,000.00")).toBeInTheDocument();
    expect(screen.getByText("Security-only HHI")).toBeInTheDocument();
    expect(screen.getByText("0.810")).toBeInTheDocument();
  });

  it("renders server-provided benchmark correlation", async () => {
    installSuccessfulFetch();
    renderPage();

    const label = await screen.findByText("Benchmark correlation");
    const card = label.closest("article");

    expect(card).not.toBeNull();
    expect(within(card!).getByText("0.98")).toBeInTheDocument();
    expect(
      within(card!).getByText("40 aligned observations"),
    ).toBeInTheDocument();
  });

  it("renders explicit Not available values with associated server diagnostics", async () => {
    const analytics = analyticsFixture();

    analytics.annualized_volatility = null;
    analytics.sharpe = null;
    analytics.sortino = null;
    analytics.beta = null;
    analytics.benchmark_correlation = null;
    analytics.benchmark_observations = null;

    analytics.warnings = [
      {
        code: "INSUFFICIENT_HISTORY",
        message:
          "Volatility, Sharpe, and Sortino require at least 30 daily return observations.",
        observations: 12,
      },
      {
        code: "BENCHMARK_NOT_CONFIGURED",
        message: "Portfolio has no configured benchmark asset.",
        observations: null,
      },
    ];

    analytics.provenance.benchmark = null;
    analytics.provenance.warnings = analytics.warnings.map(
      (warning) => warning.message,
    );

    installSuccessfulFetch(analytics);
    renderPage();

    expect(
      await screen.findByText("Limited history"),
    ).toBeInTheDocument();

    const volatility = screen
      .getByText("Annualized volatility")
      .closest("article");
    const sharpe = screen
      .getByText("Sharpe ratio")
      .closest("article");
    const beta = screen.getByText("Beta").closest("article");
    const correlation = screen
      .getByText("Benchmark correlation")
      .closest("article");

    expect(
      within(volatility!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(sharpe!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(beta!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(correlation!).getByText("Not available"),
    ).toBeInTheDocument();

    expect(
      within(volatility!).getByText(
        /require at least 30 daily return observations/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(beta!).getByText(
        "Portfolio has no configured benchmark asset.",
      ),
    ).toBeInTheDocument();
    expect(
      within(correlation!).getByText(
        "Portfolio has no configured benchmark asset.",
      ),
    ).toBeInTheDocument();
  });

  it("renders server-calculated rolling returns without client recomputation", async () => {
    installSuccessfulFetch(analyticsFixtureWithRolling());

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M&rollingWindow=20`,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Rolling returns",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("20-observation window"),
    ).toBeInTheDocument();
    expect(screen.getByText("+3.50%")).toBeInTheDocument();
    expect(screen.getByText("+4.50%")).toBeInTheDocument();
  });

  it("shows an explicit rolling-return selection state when no window is supplied", async () => {
    installSuccessfulFetch();
    renderPage();

    expect(
      await screen.findByText("Choose a rolling window"),
    ).toBeInTheDocument();
  });

  it("shows the server diagnostic when the selected rolling window exceeds available history", async () => {
  const analytics = analyticsFixture();

  analytics.rolling_return_window = 100;
  analytics.rolling_returns = [];
  analytics.warnings = [
    {
      code: "INSUFFICIENT_ROLLING_HISTORY",
      message:
        "Rolling return requires at least 100 daily return observations.",
      observations: 42,
    },
  ];

  installSuccessfulFetch(analytics);

  renderPage(
    `/portfolios/${PORTFOLIO_ID}/analysis?range=6M&rollingWindow=100`,
  );

  const rollingHeading = await screen.findByRole("heading", {
    name: "Rolling returns",
  });

  const rollingSection = rollingHeading.closest("section");

  expect(rollingSection).not.toBeNull();

  expect(
    within(rollingSection!).getByText(
      "Rolling return unavailable",
    ),
  ).toBeInTheDocument();

  expect(
    within(rollingSection!).getByText(
      "Rolling return requires at least 100 daily return observations.",
    ),
  ).toBeInTheDocument();

  expect(
    screen.getByText("100-observation window"),
  ).toBeInTheDocument();
});

  it("renders undefined benchmark correlation with the server diagnostic", async () => {
    const analytics = analyticsFixture();

    analytics.benchmark_correlation = {
      value: null,
      observations: 40,
      warnings: [
        {
          code: "ZERO_BENCHMARK_VARIANCE",
          message:
            "Correlation is undefined because benchmark sample variance is zero.",
        },
      ],
    };

    analytics.warnings = [
      {
        code: "UNDEFINED_CORRELATION",
        message:
          "Correlation is undefined because benchmark sample variance is zero.",
        observations: 40,
      },
    ];

    installSuccessfulFetch(analytics);
    renderPage();

    const label = await screen.findByText("Benchmark correlation");
    const card = label.closest("article");

    expect(card).not.toBeNull();
    expect(
      within(card!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(card!).getByText(
        "Correlation is undefined because benchmark sample variance is zero.",
      ),
    ).toBeInTheDocument();
  });

  it("renders provenance, assumptions, observations, and benchmark identity", async () => {
    installSuccessfulFetch();
    renderPage();

    expect(
      await screen.findByText("Calculation provenance"),
    ).toBeInTheDocument();
    expect(screen.getByText("mock")).toBeInTheDocument();
    expect(screen.getByText("adjusted_close")).toBeInTheDocument();
    expect(screen.getAllByText("SPY").length).toBeGreaterThan(0);
    expect(screen.getByText("0.1.0.dev0")).toBeInTheDocument();
    expect(
      screen.getByText("2026-08-01 to 2026-09-15"),
    ).toBeInTheDocument();
    expect(screen.getByText("252")).toBeInTheDocument();
    expect(
      screen.getByText("historical returns use adjusted_close"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("current allocation uses raw close"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "benchmark correlation uses Pearson correlation on exact date intersections",
      ),
    ).toBeInTheDocument();

    const portfolioObservations = screen
      .getByText("Portfolio observations")
      .closest("article");
    const benchmarkObservations = screen
      .getByText("Benchmark observations")
      .closest("article");

    expect(
      within(portfolioObservations!).getByText("42"),
    ).toBeInTheDocument();
    expect(
      within(benchmarkObservations!).getByText("40"),
    ).toBeInTheDocument();
  });

  it("preserves range context in the back link and accessible range controls", async () => {
    installSuccessfulFetch();

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
    );

    expect(await screen.findByText("Range 6M")).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Portfolio dashboard",
      }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );

    const periodControls = screen.getByRole("region", {
      name: "Analysis period controls",
    });

    const sixMonths = within(periodControls).getByRole("button", {
      name: "6M",
    });
    const oneYear = within(periodControls).getByRole("button", {
      name: "1Y",
    });

    expect(sixMonths).toHaveAttribute("aria-pressed", "true");
    expect(oneYear).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(oneYear);

    expect(oneYear).toHaveAttribute("aria-pressed", "true");
  });

  it("submits an explicit rolling window while preserving the selected range", async () => {
    const fetchMock = installSuccessfulFetch(analyticsFixtureWithRolling());

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
    );

    await screen.findByRole("heading", {
      name: "Analytical results",
    });

    fireEvent.change(
      screen.getByRole("spinbutton", {
        name: "Rolling window",
      }),
      {
        target: { value: "20" },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Apply window",
      }),
    );

    await screen.findByText("20-observation window");

    const analyticsUrls = fetchMock.mock.calls
      .map((call) => String(call[0]))
      .filter((url) =>
        url.includes(
          `/api/v1/analytics/portfolios/${PORTFOLIO_ID}/`,
        ),
      );

    expect(
      analyticsUrls.some((url) =>
        url.includes("rolling_window=20"),
      ),
    ).toBe(true);
  });

  it("shows a loading state while portfolio context is being retrieved", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>(() => undefined),
      ),
    );

    renderPage();

    expect(
      screen.getByLabelText("Loading portfolio analysis"),
    ).toBeInTheDocument();
  });

  it.each<[number, string, string, string]>([
    [
      403,
      "FORBIDDEN",
      "You do not have access to this portfolio.",
      "Portfolio access denied",
    ],
    [
      404,
      "PORTFOLIO_NOT_FOUND",
      "Portfolio was not found.",
      "Portfolio not found",
    ],
    [
      503,
      "PORTFOLIO_ANALYTICS_FAILED",
      "Analytics dependency failed.",
      "Portfolio analysis could not load",
    ],
  ])(
    "renders the expected %s analytics error state",
    async (status, code, detail, expectedTitle) => {
      installAnalyticsError(status, {
        code,
        detail,
      });

      renderPage();

      expect(
        await screen.findByText(expectedTitle),
      ).toBeInTheDocument();
    
      expect(screen.getByText(detail)).toBeInTheDocument();

      expect(
        screen.getByRole("button", {
          name: "Retry",
        }),
      ).toBeInTheDocument();
    },
  );
});