import { expect, test } from "@playwright/test";

import { loginSampleUser } from "./support";

test("create portfolio, record Activity transaction, configure benchmark, and refresh authoritative dashboard state", async ({
  page,
}) => {
  await loginSampleUser(page);

  await page.getByRole("link", { name: "Portfolios", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Portfolios", exact: true }),
  ).toBeVisible();

  const name = "E2E Cash Portfolio";
  await page.getByLabel("Portfolio name").fill(name);
  await page.getByRole("button", { name: "Create portfolio" }).click();

  await expect(
    page.getByRole("heading", { name: "Activity & Transactions" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name })).toBeVisible();

  const activitySelector = page.getByLabel("Activity portfolio");
  await activitySelector.focus();
  await expect(activitySelector).toBeFocused();
  await expect(activitySelector).not.toHaveValue("");

  await page.getByLabel("Occurred at").fill("2026-09-15T12:00");
  await page.getByLabel("Cash amount").fill("2500");
  await page.getByRole("button", { name: "Record transaction" }).click();
  await expect(page.getByText(/DEPOSIT transaction recorded/)).toBeVisible();

  const transactionHistory = page.getByRole("table", {
    name: "Complete transaction history for the selected portfolio",
  });
  await expect(transactionHistory).toBeVisible();
  await expect(transactionHistory.getByText("Deposit")).toBeVisible();
  await expect(transactionHistory.getByText("2,500")).toBeVisible();

  await page.getByRole("link", { name: "Manage portfolio" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await page
    .getByLabel("Benchmark asset")
    .selectOption({ label: "SPY — SPDR S&P 500 ETF Trust" });
  await page.getByRole("button", { name: "Save benchmark" }).click();
  await expect(page.getByText("Benchmark selection saved.")).toBeVisible();

  await page.getByRole("link", { name: "Portfolio dashboard" }).click();
  await expect(page.getByText("Portfolio summary")).toBeVisible();
  await expect(page.getByText("$2,500.00").first()).toBeVisible();
});

test("Activity is reachable from keyboard-accessible primary navigation", async ({ page }) => {
  await loginSampleUser(page);

  const activityLink = page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("link", { name: "Activity and Transactions" });

  await activityLink.focus();
  await expect(activityLink).toBeFocused();
  await activityLink.press("Enter");

  await expect(
    page.getByRole("heading", { name: "Activity & Transactions" }),
  ).toBeVisible();
  await expect(activityLink).toHaveAttribute("aria-current", "page");
});

test("an empty portfolio can be permanently deleted from Portfolio management", async ({
  page,
}) => {
  await loginSampleUser(page);

  await page.getByRole("link", { name: "Portfolios", exact: true }).click();
  const name = "E2E Empty Portfolio";
  await page.getByLabel("Portfolio name").fill(name);
  await page.getByRole("button", { name: "Create portfolio" }).click();

  await expect(
    page.getByRole("heading", { name: "Activity & Transactions" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Manage portfolio" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();

  await page.getByRole("button", { name: "Delete portfolio" }).click();
  const dialog = page.getByRole("alertdialog", {
    name: `Permanently delete ${name}?`,
  });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Permanently delete portfolio" }).click();

  await expect(page).toHaveURL(/\/portfolios$/);
  await expect(
    page.getByRole("heading", { name: "Portfolios", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name })).toHaveCount(0);
});
