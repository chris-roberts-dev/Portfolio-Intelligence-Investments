import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { PortfolioManagementPage } from "./PortfolioManagementPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_ID = "00000000-0000-0000-0000-000000000011";

const portfolio = {
  id: PORTFOLIO_ID,
  name: "Primary portfolio",
  base_currency: "USD",
  benchmark_asset_id: null,
  created_at: "2025-01-02T15:00:00Z",
  updated_at: "2026-09-15T22:00:00Z",
};

const asset = {
  id: ASSET_ID,
  symbol: "SPY",
  name: "SPDR S&P 500 ETF Trust",
  asset_type: "ETF",
  exchange: "NYSEARCA",
  currency: "USD",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function createQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0 },
      mutations: { retry: false },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
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
      <MemoryRouter
        initialEntries={[
          `/portfolios/${PORTFOLIO_ID}/manage?range=6M`,
        ]}
      >
        <Routes>
          <Route
            path="/portfolios/:portfolioId/manage"
            element={<PortfolioManagementPage />}
          />
          <Route
            path="/portfolios"
            element={<div>Portfolio list destination</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function baseFetch(
  handler?: (url: string, init?: RequestInit) => Promise<Response> | Response | null,
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const handled = await handler?.(url, init);
    if (handled) {
      return handled;
    }

    if (url.endsWith("/api/v1/portfolios/")) {
      return jsonResponse([portfolio]);
    }

    if (url.endsWith("/api/v1/assets/")) {
      return jsonResponse([asset]);
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PortfolioManagementPage", () => {
  it("keeps configuration in Portfolios and links transaction ingestion to Activity", async () => {
    baseFetch();
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Primary portfolio" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Portfolio dashboard" }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );
    expect(
      screen.getAllByRole("link", { name: /Activity & Transactions|Add or import transactions/ })[0],
    ).toHaveAttribute(
      "href",
      `/activity?portfolio=${PORTFOLIO_ID}`,
    );
    expect(
      screen.queryByRole("button", { name: "Record transaction" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("CSV file"),
    ).not.toBeInTheDocument();
  });

  it("renames through the owner-scoped API", async () => {
    document.cookie = "csrftoken=rename-page; path=/";
    let renamed = false;
    const fetchMock = baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/`) &&
        init?.method === "PATCH"
      ) {
        renamed = true;
        return jsonResponse({ ...portfolio, name: "Renamed portfolio" });
      }

      if (url.endsWith("/api/v1/portfolios/") && renamed) {
        return jsonResponse([{ ...portfolio, name: "Renamed portfolio" }]);
      }

      return null;
    });

    renderPage();

    const nameInput = await screen.findByLabelText("Portfolio name");
    fireEvent.change(nameInput, { target: { value: "Renamed portfolio" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByText("Portfolio name saved.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ name: "Renamed portfolio" }),
      }),
    );
  });


  it("permanently deletes an empty owned portfolio after explicit confirmation", async () => {
    document.cookie = "csrftoken=delete-page; path=/";
    const fetchMock = baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/`) &&
        init?.method === "DELETE"
      ) {
        return new Response(null, { status: 204 });
      }

      return null;
    });

    renderPage();

    await screen.findByRole("heading", { name: "Primary portfolio" });
    fireEvent.click(screen.getByRole("button", { name: "Delete portfolio" }));

    expect(
      screen.getByRole("alertdialog", {
        name: "Permanently delete Primary portfolio?",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Permanently delete portfolio" }),
    );

    expect(
      await screen.findByText("Portfolio list destination"),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/`,
      expect.objectContaining({
        method: "DELETE",
        credentials: "include",
      }),
    );
  });

  it("closes the delete confirmation with Escape and returns keyboard focus", async () => {
    baseFetch();
    renderPage();

    await screen.findByRole("heading", { name: "Primary portfolio" });
    const deleteButton = screen.getByRole("button", { name: "Delete portfolio" });
    deleteButton.focus();
    fireEvent.click(deleteButton);

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    fireEvent.keyDown(cancelButton, { key: "Escape" });

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(deleteButton).toHaveFocus();
  });


  it("renders the server-authoritative deletion block without navigating", async () => {
    document.cookie = "csrftoken=delete-blocked-page; path=/";
    baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/`) &&
        init?.method === "DELETE"
      ) {
        return jsonResponse(
          {
            code: "PORTFOLIO_DELETE_BLOCKED",
            detail:
              "This portfolio contains retained transaction or analytical history and cannot currently be permanently deleted.",
          },
          409,
        );
      }

      return null;
    });

    renderPage();

    await screen.findByRole("heading", { name: "Primary portfolio" });
    fireEvent.click(screen.getByRole("button", { name: "Delete portfolio" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Permanently delete portfolio" }),
    );

    expect(
      await screen.findByText(
        "This portfolio contains retained transaction or analytical history and cannot currently be permanently deleted.",
      ),
    ).toHaveAttribute("role", "alert");
    expect(
      screen.getByRole("alertdialog", {
        name: "Permanently delete Primary portfolio?",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Portfolio list destination")).not.toBeInTheDocument();
  });

  it("selects a canonical benchmark through the owner-scoped API", async () => {
    document.cookie = "csrftoken=benchmark-page; path=/";
    const fetchMock = baseFetch((url, init) => {
      if (
        url.endsWith(`/api/v1/portfolios/${PORTFOLIO_ID}/benchmark/`) &&
        init?.method === "PATCH"
      ) {
        return jsonResponse({
          ...portfolio,
          benchmark_asset_id: ASSET_ID,
        });
      }

      return null;
    });

    renderPage();

    const benchmarkSelect = await screen.findByLabelText("Benchmark asset");
    fireEvent.change(benchmarkSelect, { target: { value: ASSET_ID } });
    fireEvent.click(screen.getByRole("button", { name: "Save benchmark" }));

    expect(
      await screen.findByText("Benchmark selection saved."),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/portfolios/${PORTFOLIO_ID}/benchmark/`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ benchmark_asset_id: ASSET_ID }),
      }),
    );
  });
});
