import { expect, test } from "@playwright/test";

import { loginSampleUser, SAMPLE_PORTFOLIO_ID } from "./support";

test("owned portfolio can create an optimization target and compare deterministic rebalancing rules", async ({
  page,
}) => {
  await loginSampleUser(page);

  await page.goto(`/portfolios/${SAMPLE_PORTFOLIO_ID}/allocation-lab`);
  await expect(page.getByRole("heading", { name: "Allocation Lab" })).toBeVisible();

  await page.getByRole("button", { name: "Import current holdings" }).click();

  // Use the canonical per-asset configuration controls rather than bare ticker
  // text, because the page intentionally displays each symbol in more than one
  // place after import.
  await expect(page.getByLabel("AAPL minimum weight")).toBeVisible();
  await expect(page.getByLabel("MSFT minimum weight")).toBeVisible();

  await page.getByLabel("Analysis start").fill("2026-02-02");
  await page.getByLabel("End (exclusive)").fill("2026-09-16");
  await page.getByLabel("Optimization method").selectOption("MINIMUM_VARIANCE");
  await page.getByRole("button", { name: "Run optimization" }).click();

  const persistedRunLabel = page.getByText("Persisted run", { exact: true });
  await expect(persistedRunLabel).toBeVisible();

  const persistedRun = persistedRunLabel.locator("..").locator("..");
  await expect(
    persistedRun.getByText("Succeeded", { exact: true }),
  ).toBeVisible();

  await page.goto(`/portfolios/${SAMPLE_PORTFOLIO_ID}/rebalancing-lab`);
  await expect(page.getByRole("heading", { name: "Rebalancing Lab" })).toBeVisible();

  const runSelect = page.getByLabel("Successful optimization run");
  await expect(runSelect.locator("option")).toHaveCount(2);
  await runSelect.selectOption({ index: 1 });
  await page.getByLabel("Target name").fill("Playwright minimum variance target");
  await page.getByRole("button", { name: "Save target" }).click();

  await expect(page.getByLabel("Saved target allocation")).not.toHaveValue("");

  await page.getByRole("button", { name: "Simulate current rebalance" }).click();

  const currentSimulation = page.getByRole("region", {
    name: "Current rebalance simulation detail",
  });
  await expect(currentSimulation).toBeVisible();
  await expect(
    currentSimulation.getByRole("columnheader", { name: "Absolute drift" }),
  ).toBeVisible();
  await expect(
    currentSimulation.getByRole("columnheader", { name: "Relative drift" }),
  ).toBeVisible();
  await expect(
    currentSimulation.getByRole("columnheader", { name: "Simulated trade" }),
  ).toBeVisible();
  await expect(
    currentSimulation.getByRole("rowheader", { name: "AAPL", exact: true }),
  ).toBeVisible();

  await page.getByLabel("Historical period start").fill("2026-02-02");
  await page.getByLabel("Historical period end").fill("2026-09-15");
  await page.getByLabel("Absolute drift threshold").fill("0.05");
  await page.getByRole("button", { name: "Run historical comparison" }).click();

  const results = page.getByRole("region", {
    name: "Historical rebalancing comparison results",
  });
  await expect(results).toBeVisible();

  const policyComparisonTable = results.getByRole("table", {
    name: "Actual portfolio and historical rebalancing policy comparison",
  });
  await expect(policyComparisonTable).toBeVisible();

  await expect(
    policyComparisonTable.getByRole("rowheader", {
      name: "Actual portfolio",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    policyComparisonTable.getByRole("button", {
      name: "Annual",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    policyComparisonTable.getByRole("button", {
      name: "Quarterly",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    policyComparisonTable.getByRole("button", {
      name: "Drift threshold",
      exact: true,
    }),
  ).toBeVisible();

  for (const heading of ["Vs actual", "Turnover", "Max drift", "Total costs"]) {
    await expect(
      policyComparisonTable.getByRole("columnheader", {
        name: heading,
        exact: true,
      }),
    ).toBeVisible();
  }

  await expect(
    results.getByRole("region", {
      name: "Actual portfolio comparison baseline",
    }),
  ).toBeVisible();
  await expect(
    results.getByRole("heading", {
      name: "Growth of $100",
      exact: true,
    }),
  ).toBeVisible();

  await expect(
    page.getByRole("region", { name: "Historical comparison assumptions and provenance" }),
  ).toContainText("adjusted_close");
  await expect(
    page.getByRole("region", { name: "Historical comparison assumptions and provenance" }),
  ).toContainText("csv");
  await expect(
    page.getByRole("region", { name: "Historical comparison assumptions and provenance" }),
  ).toContainText("TIME_WEIGHTED");
  const historicalWarnings = page
    .getByLabel("Rebalancing warnings")
    .filter({ hasText: "Actual ledger activity ignored" });

  await expect(historicalWarnings).toBeVisible();
  await expect(historicalWarnings).toContainText(
    "Actual ledger activity ignored",
  );

  const policyDetail = page.getByRole("heading", {
    name: "Annual event detail",
    exact: true,
  });
  await expect(policyDetail).toBeVisible();

  const eventTable = page.getByRole("table", {
    name: "Rebalance decision and execution events",
  });
  await expect(eventTable).toBeVisible();
  await expect(
    eventTable.getByRole("columnheader", {
      name: "Decision date",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    eventTable.getByRole("columnheader", {
      name: "Execution date",
      exact: true,
    }),
  ).toBeVisible();
});
