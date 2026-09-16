import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { HomePage } from "./HomePage";

function renderHome() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, retryDelay: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<HomePage />} />
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

describe("HomePage portfolio creation", () => {
  it("creates an owned portfolio and moves directly into the ingestion flow", async () => {
    document.cookie = "csrftoken=create-portfolio-page; path=/";
    const portfolio = {
      id: "00000000-0000-0000-0000-000000000002",
      name: "Long-term portfolio",
      base_currency: "USD",
      benchmark_asset_id: null,
      created_at: "2026-09-16T12:00:00Z",
      updated_at: "2026-09-16T12:00:00Z",
    };
    let created = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith("/api/v1/portfolios/") && init?.method === "POST") {
        created = true;
        return new Response(JSON.stringify(portfolio), {
          status: 201,
          headers: { "content-type": "application/json" },
        });
      }

      if (url.endsWith("/api/v1/portfolios/")) {
        return new Response(JSON.stringify(created ? [portfolio] : []), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderHome();

    fireEvent.change(await screen.findByLabelText("Portfolio name"), {
      target: { value: "Long-term portfolio" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create portfolio" }));

    expect(
      await screen.findByRole("heading", { name: "Manage created portfolio" }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/portfolios/",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "Long-term portfolio" }),
      }),
    );
  });

  it("renders server portfolio-name validation without optimistic navigation", async () => {
    document.cookie = "csrftoken=create-portfolio-error; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);

        if (url.endsWith("/api/v1/portfolios/") && init?.method === "POST") {
          return new Response(
            JSON.stringify({
              code: "VALIDATION_ERROR",
              errors: { name: ["Name is already in use."] },
            }),
            {
              status: 400,
              headers: { "content-type": "application/json" },
            },
          );
        }

        if (url.endsWith("/api/v1/portfolios/")) {
          return new Response(JSON.stringify([]), {
            status: 200,
            headers: { "content-type": "application/json" },
          });
        }

        throw new Error(`Unexpected request: ${url}`);
      }),
    );

    renderHome();

    fireEvent.change(await screen.findByLabelText("Portfolio name"), {
      target: { value: "Duplicate" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create portfolio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Name is already in use.",
    );
    expect(
      screen.queryByRole("heading", { name: "Manage created portfolio" }),
    ).not.toBeInTheDocument();
  });
});
