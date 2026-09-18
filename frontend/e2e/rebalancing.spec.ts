import { expect, test } from "@playwright/test";

import { loginSampleUser, SAMPLE_PORTFOLIO_ID } from "./support";

test("owned portfolio can create an optimization target and compare deterministic rebalancing rules", async ({
  page,
}) => {
  await loginSampleUser(page);

  await page.goto(`/portfolios/${SAMPLE_PORTFOLIO_ID}/allocation-lab`);
  await expect(page.getByRole("heading", { name: "Allocation Lab" })).toBeVisible();

  await page.getByRole("button", { name: "Import current holdings" }).click();
  await expect(page.getByText("AAPL", { exact: true })).toBeVisible();
  await expect(page.getByText("MSFT", { exact: true })).toBeVisible();

  await page.getByLabel("Analysis start").fill("2026-02-02");
  await page.getByLabel("End (exclusive)").fill("2026-09-16");
  await page.getByLabel("Optimization method").selectOption("MINIMUM_VARIANCE");
  await page.getByRole("button", { name: "Run optimization" }).click();

  await expect(page.getByText("Persisted run")).toBeVisible();
  await expect(page.getByText("Succeeded", { exact: true })).toBeVisible();

  await page.goto(`/portfolios/${SAMPLE_PORTFOLIO_ID}/rebalancing-lab`);
  await expect(page.getByRole("heading", { name: "Rebalancing Lab" })).toBeVisible();

  const runSelect = page.getByLabel("Successful optimization run");
  await expect(runSelect.locator("option")).toHaveCount(2);
  await runSelect.selectOption({ index: 1 });
  await page.getByLabel("Target name").fill("Playwright minimum variance target");
  await page.getByRole("button", { name: "Save target" }).click();

  await expect(page.getByLabel("Saved target allocation")).not.toHaveValue("");

  await page.getByRole("button", { name: "Simulate current rebalance" }).click();
  await expect(page.getByText("Simulated trade")).toBeVisible();
  await expect(page.getByText("AAPL", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Threshold status")).toBeVisible();

  await page.getByLabel("Historical period start").fill("2026-02-02");
  await page.getByLabel("Historical period end").fill("2026-09-15");
  await page.getByLabel("Absolute drift threshold").fill("0.05");
  await page.getByRole("button", { name: "Run historical comparison" }).click();

  const results = page.getByRole("region", {
    name: "Historical rebalancing comparison results",
  });
  await expect(results).toBeVisible();
  await expect(results.getByRole("button", { name: "Annual" })).toBeVisible();
  await expect(results.getByRole("button", { name: "Quarterly" })).toBeVisible();
  await expect(results.getByRole("button", { name: "Drift threshold" })).toBeVisible();
  await expect(results.getByText("Turnover")).toBeVisible();
  await expect(results.getByText("Max drift")).toBeVisible();
  await expect(results.getByText("Total costs")).toBeVisible();

  await expect(
    page.getByRole("region", { name: "Historical comparison assumptions and provenance" }),
  ).toContainText("adjusted_close");
  await expect(
    page.getByRole("region", { name: "Historical comparison assumptions and provenance" }),
  ).toContainText("csv");
  await expect(page.getByLabel("Rebalancing warnings")).toContainText(
    "Actual ledger activity ignored",
  );

  const policyDetail = page.getByRole("heading", { name: "Annual event detail" });
  await expect(policyDetail).toBeVisible();
  await expect(page.getByText("Decision date")).toBeVisible();
  await expect(page.getByText("Execution date")).toBeVisible();
});
