import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { App } from "./App";

describe("App", () => {
  it("renders the Phase 1 application shell", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Portfolio Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Phase 1 foundation")).toBeInTheDocument();
  });
});