import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { PropsWithChildren } from "react";

import {
  useConfirmPortfolioTransactionImport,
  useCreatePortfolio,
  useCreatePortfolioTransaction,
  useDeletePortfolio,
  useRenamePortfolio,
  useUpdatePortfolioBenchmark,
} from "./usePortfolioData";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("portfolio management query invalidation", () => {

  it("invalidates only the portfolio list after create and rename mutations", async () => {
    document.cookie = "csrftoken=portfolio-mutation-hook; path=/";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const name = init?.method === "PATCH" ? "Renamed" : "Created";
      return new Response(
        JSON.stringify({
          id: PORTFOLIO_ID,
          name,
          base_currency: "USD",
          benchmark_asset_id: null,
          created_at: "2026-09-16T12:00:00Z",
          updated_at: "2026-09-16T12:00:00Z",
        }),
        {
          status: url.includes("/portfolios/") ? 200 : 500,
          headers: { "content-type": "application/json" },
        },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const createHook = renderHook(() => useCreatePortfolio(), {
      wrapper: createWrapper(queryClient),
    });
    const renameHook = renderHook(() => useRenamePortfolio(PORTFOLIO_ID), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await createHook.result.current.mutateAsync({ name: "Created" });
      await renameHook.result.current.mutateAsync({ name: "Renamed" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolios"],
    });
    expect(
      invalidateSpy.mock.calls.some(
        ([options]) =>
          options !== undefined &&
          Array.isArray(options.queryKey) &&
          options.queryKey[0] === "portfolio-dashboard",
      ),
    ).toBe(false);
  });

  it("invalidates the portfolio list and removes deleted portfolio derived caches", async () => {
    document.cookie = "csrftoken=portfolio-delete-hook; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 204 })),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    queryClient.setQueryData(
      ["portfolio-dashboard", PORTFOLIO_ID, "2026-09-01", "2026-09-17"],
      { snapshot: true },
    );
    queryClient.setQueryData(
      ["portfolio-analysis", PORTFOLIO_ID, "2026-09-01", "2026-09-17"],
      { analytics: true },
    );
    queryClient.setQueryData(
      ["portfolio-transactions", PORTFOLIO_ID],
      [{ id: "transaction" }],
    );

    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const removeSpy = vi.spyOn(queryClient, "removeQueries");
    const { result } = renderHook(() => useDeletePortfolio(PORTFOLIO_ID), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-dashboard", PORTFOLIO_ID],
    });
    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-analysis", PORTFOLIO_ID],
    });
    expect(removeSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-transactions", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolios"],
    });
    expect(
      queryClient.getQueriesData({
        queryKey: ["portfolio-dashboard", PORTFOLIO_ID],
      }),
    ).toEqual([]);
    expect(
      queryClient.getQueriesData({
        queryKey: ["portfolio-analysis", PORTFOLIO_ID],
      }),
    ).toEqual([]);
    expect(
      queryClient.getQueriesData({
        queryKey: ["portfolio-transactions", PORTFOLIO_ID],
      }),
    ).toEqual([]);
  });

  it("invalidates transaction history, dashboard, and analysis after a manual transaction", async () => {
    document.cookie = "csrftoken=manual-transaction-hook; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            id: "00000000-0000-0000-0000-000000000050",
            portfolio_id: PORTFOLIO_ID,
            transaction_type: "DEPOSIT",
            asset_id: null,
            asset_symbol: null,
            occurred_at: "2026-09-16T12:00:00Z",
            source_sequence: 0,
            quantity: null,
            price: null,
            fees: "0.00000000",
            cash_amount: "1000.00000000",
            created_at: "2026-09-16T12:00:01Z",
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(
      () => useCreatePortfolioTransaction(PORTFOLIO_ID),
      { wrapper: createWrapper(queryClient) },
    );

    await act(async () => {
      await result.current.mutateAsync({
        transaction_type: "DEPOSIT",
        occurred_at: "2026-09-16T12:00:00Z",
        cash_amount: "1000",
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolios"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-transactions", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-dashboard", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-analysis", PORTFOLIO_ID],
    });
  });

  it("invalidates history and derived reads after atomic CSV confirmation", async () => {
    document.cookie = "csrftoken=csv-confirm-hook; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            imported_count: 1,
            transactions: [],
          }),
          {
            status: 201,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(
      () => useConfirmPortfolioTransactionImport(PORTFOLIO_ID),
      { wrapper: createWrapper(queryClient) },
    );

    await act(async () => {
      await result.current.mutateAsync({ csv_text: "csv" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolios"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-transactions", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-dashboard", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-analysis", PORTFOLIO_ID],
    });
  });

  it("invalidates portfolio, dashboard, and analysis roots after benchmark selection", async () => {
    document.cookie = "csrftoken=benchmark-hook; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            id: PORTFOLIO_ID,
            name: "Portfolio",
            base_currency: "USD",
            benchmark_asset_id: "00000000-0000-0000-0000-000000000099",
            created_at: "2026-09-16T12:00:00Z",
            updated_at: "2026-09-16T12:00:00Z",
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(
      () => useUpdatePortfolioBenchmark(PORTFOLIO_ID),
      { wrapper: createWrapper(queryClient) },
    );

    await act(async () => {
      await result.current.mutateAsync({
        benchmark_asset_id: "00000000-0000-0000-0000-000000000099",
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolios"],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-dashboard", PORTFOLIO_ID],
    });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["portfolio-analysis", PORTFOLIO_ID],
    });
  });

});