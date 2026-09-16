import { expect, test } from "@playwright/test";

import { loginSampleUser } from "./support";

test("create portfolio, select benchmark, record deposit, and refresh from server state", async ({
  page,
}) => {
  await loginSampleUser(page);

  const name = "E2E Cash Portfolio";
  await page.getByLabel("Portfolio name").fill(name);
  await page.getByRole("button", { name: "Create portfolio" }).click();

  await expect(page.getByText("Manage portfolio")).toBeVisible();
  await expect(page.getByLabel("Portfolio name")).toHaveValue(name);

  await page.getByLabel("Benchmark asset").selectOption({ label: "SPY — SPDR S&P 500 ETF Trust" });
  await page.getByRole("button", { name: "Save benchmark" }).click();
  await expect(page.getByText("Benchmark selection saved.")).toBeVisible();

  await page.getByLabel("Occurred at").fill("2026-09-15T12:00");
  await page.getByLabel("Cash amount").fill("2500");
  await page.getByRole("button", { name: "Record transaction" }).click();
  await expect(page.getByText(/DEPOSIT transaction recorded/)).toBeVisible();

  await page.getByRole("link", { name: "Portfolio dashboard" }).click();
  await expect(page.getByText("Portfolio summary")).toBeVisible();
  await expect(page.getByText("$2,500.00").first()).toBeVisible();
});
