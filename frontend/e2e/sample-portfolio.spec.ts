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

  const dashboardPeriodControls = page.getByRole("group", {
    name: "Portfolio report date range",
  });
  await dashboardPeriodControls.getByRole("button", { name: "3Y" }).click();

  await expect(page).toHaveURL(/range=3Y/);
  const analysisUrl = new URL(page.url());
  analysisUrl.pathname = analysisUrl.pathname.replace(/\/dashboard$/, "/analysis");
  analysisUrl.search = "?range=3Y";
  await page.goto(analysisUrl.toString());

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
test("portfolio report exposes print-friendly content without application chrome", async ({
  page,
}) => {
  await loginSampleUser(page);
  await openSampleDashboard(page);

  await expect(
    page.getByRole("button", { name: "Print / Export PDF" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /portfolio/i }).first(),
  ).toBeVisible();

  await page.getByRole("link", { name: "Holdings", exact: true }).click();
  await expect(page.locator("#portfolio-report-detail-heading")).toHaveText("Holdings");

  await page.emulateMedia({ media: "print" });

  await expect(page.locator(".app-shell-navigation").first()).toBeHidden();
  await expect(page.locator(".app-shell-topbar")).toBeHidden();
  await expect(page.locator(".portfolio-report-page")).toBeVisible();
  await expect(page.locator("#portfolio-report-detail-heading")).toBeVisible();
  await expect(page.locator(".portfolio-report-footer")).toBeVisible();
});

test("portfolio report detail navigation preserves portfolio and reporting-period context", async ({
  page,
}) => {
  await loginSampleUser(page);
  await openSampleDashboard(page);

  const rangeControls = page.getByRole("group", {
    name: "Portfolio report date range",
  });
  await rangeControls.getByRole("button", { name: "3Y" }).click();
  await expect(page).toHaveURL(/range=3Y/);

  const holdingsTab = page.getByRole("link", { name: "Holdings", exact: true });
  await holdingsTab.focus();
  await expect(holdingsTab).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/range=3Y.*view=holdings|view=holdings.*range=3Y/);
  await expect(page.locator("#portfolio-report-detail-heading")).toHaveText("Holdings");
  await expect(
    page.getByRole("link", { name: "Holdings", exact: true }),
  ).toHaveAttribute("aria-current", "page");

  await page.getByRole("link", { name: "Allocation", exact: true }).click();
  await expect(page).toHaveURL(/range=3Y.*view=allocation|view=allocation.*range=3Y/);
  await expect(page.locator("#portfolio-report-detail-heading")).toHaveText("Allocation");

  await page.getByRole("link", { name: "Performance", exact: true }).click();
  await expect(page).toHaveURL(/range=3Y.*view=performance|view=performance.*range=3Y/);
  await expect(page.locator("#portfolio-report-detail-heading")).toHaveText("Performance");
  await expect(page.getByText("Performance period details")).toBeVisible();

  await page.getByRole("link", { name: "Risk", exact: true }).click();
  await expect(page).toHaveURL(/range=3Y.*view=risk|view=risk.*range=3Y/);
  await expect(page.locator("#portfolio-report-detail-heading")).toHaveText("Risk");
  await expect(page.getByText("Calculation context")).toBeVisible();

  await page.getByRole("link", { name: "Transactions", exact: true }).click();
  await expect(page).toHaveURL(/range=3Y.*view=transactions|view=transactions.*range=3Y/);
  await expect(page.locator("#portfolio-report-detail-heading")).toHaveText("Transactions");
  await expect(
    page.getByRole("heading", { name: "Transaction history" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Open Activity & Transactions" }),
  ).toBeVisible();
});
