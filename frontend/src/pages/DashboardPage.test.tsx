import {
    QueryClient,
    QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import {
    MemoryRouter,
    Route,
    Routes,
} from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { DashboardPage } from "./DashboardPage";

const PORTFOLIO_ID =
  "00000000-0000-0000-0000-000000000002";

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
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

afterEach(() => {
  vi.unstubAllGlobals();
});

describe(
  "DashboardPage portfolio analysis navigation",
  () => {
    it("preserves the selected portfolio and range in the analysis link", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn((input: RequestInfo | URL) => {
          const url = String(input);

          if (url.endsWith("/api/v1/portfolios/")) {
            return Promise.resolve(
              new Response(
                JSON.stringify([
                  {
                    id: PORTFOLIO_ID,
                    name: "Primary portfolio",
                    base_currency: "USD",
                    benchmark_asset_id: null,
                    created_at:
                      "2025-01-02T15:00:00Z",
                    updated_at:
                      "2026-09-15T22:00:00Z",
                  },
                ]),
                {
                  status: 200,
                  headers: {
                    "content-type":
                      "application/json",
                  },
                },
              ),
            );
          }

          if (
            url.includes(
              `/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`,
            )
          ) {
            return new Promise<Response>(
              () => undefined,
            );
          }

          throw new Error(
            `Unexpected request: ${url}`,
          );
        }),
      );

      const queryClient =
        createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter
            initialEntries={[
              `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
            ]}
          >
            <Routes>
              <Route
                path="/portfolios/:portfolioId/dashboard"
                element={<DashboardPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByRole("link", {
          name: "View portfolio analysis →",
        }),
      ).toHaveAttribute(
        "href",
        `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
      );
    });
  },
);