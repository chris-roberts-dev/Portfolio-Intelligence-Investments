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
import { MemoryRouter } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { MarketDataExplorerPage } from "./MarketDataExplorerPage";

vi.mock("../components/charts/MarketPriceChart", () => ({
  MarketPriceChart: () => (
    <div data-testid="market-price-chart">Price chart</div>
  ),
}));

vi.mock("../components/charts/MarketCandlestickChart", () => ({
  MarketCandlestickChart: ({
    result,
  }: {
    result: { symbol: string };
  }) => (
    <div data-testid="market-candlestick-chart">
      {result.symbol} candlestick chart
    </div>
  ),
}));

function queryClient(): QueryClient {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        retryDelay: 0,
      },
    },
  });

  client.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "owner@example.com",
      first_name: "Portfolio",
      last_name: "Owner",
    },
  });

  return client;
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient()}>
      <MemoryRouter initialEntries={["/market-data"]}>
        <MarketDataExplorerPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText("Ticker symbols"), {
    target: { value: " aapl, MSFT\naapl bad " },
  });
  fireEvent.change(screen.getByLabelText("Start"), {
    target: { value: "2026-09-01" },
  });
  fireEvent.change(screen.getByLabelText("End (exclusive)"), {
    target: { value: "2026-09-17" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Query" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("MarketDataExplorerPage", () => {
  it("does not query until the form is explicitly submitted", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    expect(
      screen.getByText("Submit a market-data query"),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows normalized symbol chips before submission without querying", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    fireEvent.change(screen.getByLabelText("Ticker symbols"), {
      target: { value: " msft, AAPL\nmsft spy " },
    });

    const preview = screen.getByLabelText("Normalized symbols");
    const chips = within(preview).getAllByText(/MSFT|AAPL|SPY/);

    expect(chips.map((chip) => chip.textContent)).toEqual([
      "MSFT",
      "AAPL",
      "SPY",
    ]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("preserves partial success, warnings, provenance, and successful charts", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) => {
        const body = JSON.parse(String(init?.body)) as {
          symbols: string[];
        };

        expect(body.symbols).toEqual(["AAPL", "MSFT", "BAD"]);

        return new Response(
          JSON.stringify({
            results: [
              {
                symbol: "AAPL",
                asset_id:
                  "00000000-0000-0000-0000-000000000011",
                status: "SUCCEEDED",
                bars: [
                  {
                    asset_id:
                      "00000000-0000-0000-0000-000000000011",
                    trade_date: "2026-09-15",
                    open: 100,
                    high: 106,
                    low: 99,
                    close: 105,
                    adjusted_close: 105,
                    volume: 1200,
                    source: "mock",
                    retrieved_at: "2026-09-16T13:00:00Z",
                  },
                ],
                warnings: ["Delayed provider observation."],
              },
              {
                symbol: "MSFT",
                asset_id:
                  "00000000-0000-0000-0000-000000000012",
                status: "NO_DATA",
                bars: [],
                warnings: ["No bars in requested period."],
              },
              {
                symbol: "BAD",
                asset_id: null,
                status: "NOT_FOUND",
                bars: [],
                warnings: [],
              },
            ],
            meta: {
              provider: "mock",
              retrieved_at: "2026-09-16T13:00:00Z",
              interval: "1d",
              start: "2026-09-01",
              end: "2026-09-17",
            },
            row_count: 1,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    renderPage();
    fillAndSubmit();

    expect(
      await screen.findByText("Partial success"),
    ).toBeInTheDocument();
    expect(screen.getByText("mock · 1d")).toBeInTheDocument();
    expect(
      screen.getByText("2026-09-01 to 2026-09-17 (end exclusive)"),
    ).toBeInTheDocument();

    const statusSection = screen
      .getByRole("heading", { name: "Symbol status" })
      .closest("section");

    expect(statusSection).not.toBeNull();
    expect(within(statusSection!).getByText("Succeeded")).toBeInTheDocument();
    expect(within(statusSection!).getByText("No data")).toBeInTheDocument();
    expect(within(statusSection!).getByText("Not found")).toBeInTheDocument();
    expect(
      within(statusSection!).getByText("Delayed provider observation."),
    ).toBeInTheDocument();
    expect(
      within(statusSection!).getByText("No bars in requested period."),
    ).toBeInTheDocument();

    expect(
      screen.getByTestId("market-price-chart"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("market-candlestick-chart"),
    ).toHaveTextContent("AAPL candlestick chart");
  });

  it("shows an accessible loading state", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => undefined)),
    );

    renderPage();
    fillAndSubmit();

    expect(
      screen.getByLabelText("Loading market data"),
    ).toBeInTheDocument();
  });

  it("shows provider failure with retry without hiding the query form", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            code: "PROVIDER_INITIALIZATION_FAILED",
            detail: "Configured provider is unavailable.",
          }),
          {
            status: 503,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    renderPage();
    fillAndSubmit();

    expect(
      await screen.findByText("Market-data provider unavailable"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Configured provider is unavailable."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Retry" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Query" }),
    ).toBeInTheDocument();
  });

  it("exposes the Market data primary navigation destination", () => {
    vi.stubGlobal("fetch", vi.fn());

    renderPage();

    const links = screen.getAllByRole("link", { name: "Market data" });

    expect(links.length).toBeGreaterThan(0);
    expect(links.every((link) => link.getAttribute("href") === "/market-data")).toBe(
      true,
    );
  });
});
