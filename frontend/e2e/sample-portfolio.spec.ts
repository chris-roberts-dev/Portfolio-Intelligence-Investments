import { expect, test } from "@playwright/test";

import { loginSampleUser, openSampleDashboard } from "./support";

test("sample portfolio exposes deterministic dashboard and portfolio analytics", async ({
  page,
}) => {
  await loginSampleUser(page);
  await openSampleDashboard(page);

  await expect(page.getByText("Portfolio summary")).toBeVisible();
  await expect(page.getByText("Allocation").first()).toBeVisible();

  const currentValueRow = page.getByText("Total market value").locator("..");
  await expect(currentValueRow).toBeVisible();
  await expect(currentValueRow).not.toContainText("Not available");

  const dashboardPeriodControls = page.getByRole("region", {
    name: "Dashboard period controls",
  });
  await dashboardPeriodControls.getByRole("button", { name: "6M" }).click();

  const analysisLink = page.getByRole("link", {
    name: /View portfolio analysis/,
  });
  await expect(analysisLink).toHaveAttribute("href", /range=6M/);
  await analysisLink.click();

  await expect(
    page.getByRole("heading", { name: "Analytical results" }),
  ).toBeVisible();

  for (const label of [
    "Sharpe ratio",
    "Sortino ratio",
    "Maximum drawdown",
    "Beta",
    "Benchmark correlation",
  ]) {
    const metric = page.getByText(label, { exact: true }).locator("..");
    await expect(metric).toBeVisible();
    await expect(metric).not.toContainText("Not available");
  }

  await expect(page.getByText("SPY").first()).toBeVisible();

  await page.getByLabel("Rolling window").fill("21");
  await page.getByRole("button", { name: "Apply window" }).click();
  await expect(page.getByText("21-observation window")).toBeVisible();

  const periodControls = page.getByRole("region", {
    name: "Analysis period controls",
  });
  await periodControls.getByRole("button", { name: "1W" }).click();
  await expect(page.getByText("Limited history")).toBeVisible();
  await expect(page.getByRole("link", { name: "Portfolio dashboard" })).toHaveAttribute(
    "href",
    /range=1W/,
  );
});
