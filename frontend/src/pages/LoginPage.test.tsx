import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { LoginPage } from "./LoginPage";

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/login",
            state: {
              from: "/portfolios/portfolio-1/dashboard?range=3M",
            },
          },
        ]}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/portfolios/:portfolioId/dashboard"
            element={<h1>Returned dashboard</h1>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("successful login returns to the originally requested protected URL", async () => {
  document.cookie = "csrftoken=login-test-token; path=/";
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.endsWith("/api/v1/auth/session/")) {
      return new Response(
        JSON.stringify({ authenticated: false, user: null }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      );
    }

    if (url.endsWith("/api/v1/auth/login/")) {
      return new Response(
        JSON.stringify({
          authenticated: true,
          user: {
            id: "00000000-0000-0000-0000-000000000001",
            email: "owner@example.com",
            first_name: "Portfolio",
            last_name: "Owner",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderLogin();

  fireEvent.change(await screen.findByLabelText("Email"), {
    target: { value: "owner@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "secret-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(
    await screen.findByRole("heading", { name: "Returned dashboard" }),
  ).toBeInTheDocument();
});
