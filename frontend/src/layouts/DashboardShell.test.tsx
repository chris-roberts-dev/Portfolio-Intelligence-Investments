import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { DashboardShell } from "./DashboardShell";

function renderShell(pathname: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
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

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[pathname]}>
        <DashboardShell header={<h1>Page heading</h1>}>
          <p>Page content</p>
        </DashboardShell>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardShell", () => {
  it("renders visible primary-domain labels and identifies the current destination", () => {
    renderShell("/portfolios/example/dashboard");

    expect(screen.getAllByRole("link", { name: "Overview" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Portfolios" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Market data" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Allocation Lab" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Rebalancing Lab" }).length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("link", { name: "Activity and Transactions" }).length,
    ).toBeGreaterThan(0);

    expect(
      screen.getAllByRole("link", { name: "Portfolios" }).some(
        (link) => link.getAttribute("aria-current") === "page",
      ),
    ).toBe(true);
  });


  it("marks Rebalancing Lab active independently of portfolio navigation", () => {
    renderShell("/portfolios/example/rebalancing-lab");

    const links = screen.getAllByRole("link", { name: "Rebalancing Lab" });
    expect(
      links.some((link) => link.getAttribute("aria-current") === "page"),
    ).toBe(true);
    expect(
      screen.getAllByRole("link", { name: "Portfolios" }).some(
        (link) => link.getAttribute("aria-current") === "page",
      ),
    ).toBe(false);
  });

  it("marks Activity and Transactions active and keeps navigation keyboard focusable", () => {
    renderShell("/activity?portfolio=00000000-0000-0000-0000-000000000002");

    const activityLinks = screen.getAllByRole("link", {
      name: "Activity and Transactions",
    });
    expect(
      activityLinks.some((link) => link.getAttribute("aria-current") === "page"),
    ).toBe(true);

    activityLinks[0]?.focus();
    expect(activityLinks[0]).toHaveFocus();
  });

  it("provides an accessible mobile navigation drawer", () => {
    renderShell("/");

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));

    expect(
      screen.getByRole("button", { name: "Close navigation panel" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Portfolios" }).length).toBeGreaterThan(1);
  });
});
