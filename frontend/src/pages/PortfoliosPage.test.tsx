import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { PortfoliosPage } from "./PortfoliosPage";

function createQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0 },
      mutations: { retry: false },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000001",
      email: "owner@example.com",
      first_name: "Portfolio",
      last_name: "Owner",
    },
  });

  return queryClient;
}

function renderPage() {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={["/portfolios"]}>
        <Routes>
          <Route path="/portfolios" element={<PortfoliosPage />} />
          <Route
            path="/portfolios/:portfolioId/manage"
            element={<h1>Manage created portfolio</h1>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PortfoliosPage", () => {
  it("owns portfolio creation and routes successful creation into portfolio management", async () => {
    document.cookie = "csrftoken=create-portfolio-page; path=/";
    const createdPortfolio = {
      id: "00000000-0000-0000-0000-000000000002",
      name: "Long-term portfolio",
      base_currency: "USD",
      benchmark_asset_id: null,
      created_at: "2026-09-16T12:00:00Z",
      updated_at: "2026-09-16T12:00:00Z",
    };
    let created = false;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);

        if (url.endsWith("/api/v1/portfolios/") && init?.method === "POST") {
          created = true;
          return new Response(JSON.stringify(createdPortfolio), {
            status: 201,
            headers: { "content-type": "application/json" },
          });
        }

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify(created ? [createdPortfolio] : []), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage();

    fireEvent.change(await screen.findByLabelText("Portfolio name"), {
      target: { value: "Long-term portfolio" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create portfolio" }));

    expect(
      await screen.findByRole("heading", { name: "Manage created portfolio" }),
    ).toBeInTheDocument();
  });

  it("lists owned portfolios with Overview, detailed dashboard, and management destinations", async () => {
    const portfolio = {
      id: "00000000-0000-0000-0000-000000000002",
      name: "Primary portfolio",
      base_currency: "USD",
      benchmark_asset_id: null,
      created_at: "2026-09-16T12:00:00Z",
      updated_at: "2026-09-16T12:00:00Z",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify([portfolio]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }
        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderPage();

    expect(await screen.findByText("Primary portfolio")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Overview" })).toHaveAttribute(
      "href",
      `/?portfolio=${portfolio.id}&range=YTD`,
    );
    expect(
      screen.getByRole("link", { name: "Detailed dashboard" }),
    ).toHaveAttribute("href", `/portfolios/${portfolio.id}/dashboard?range=1M`);
    expect(screen.getByRole("link", { name: "Manage" })).toHaveAttribute(
      "href",
      `/portfolios/${portfolio.id}/manage?range=1M`,
    );
  });
});
