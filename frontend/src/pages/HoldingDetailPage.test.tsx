import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { HoldingDetailPage } from "./HoldingDetailPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_ID = "00000000-0000-0000-0000-000000000012";

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

describe("HoldingDetailPage", () => {
  it("preserves the selected portfolio and time-range context", () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter
          initialEntries={[
            {
              pathname: `/portfolios/${PORTFOLIO_ID}/holdings/${ASSET_ID}`,
              search: "?range=6M",
              state: {
                holding: {
                  assetId: ASSET_ID,
                  symbol: "BBB",
                  name: "BBB Incorporated",
                  assetType: "STOCK",
                  currency: "USD",
                },
              },
            },
          ]}
        >
          <Routes>
            <Route
              path="/portfolios/:portfolioId/holdings/:assetId"
              element={<HoldingDetailPage />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "BBB" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("BBB Incorporated"),
    ).toBeInTheDocument();
    expect(screen.getByText("Range 6M")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "← Back to portfolio dashboard",
      }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );
  });
});