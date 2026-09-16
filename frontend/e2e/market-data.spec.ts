import { expect, test } from "@playwright/test";

import { loginSampleUser } from "./support";

test("market explorer keeps valid symbols usable during deterministic partial success", async ({
  page,
}) => {
  await loginSampleUser(page);
  await page.getByRole("link", { name: "Market data" }).first().click();

  await page.getByLabel("Ticker symbols").fill("AAPL, MSFT\nNODATA");
  await page.getByLabel("Start").fill("2026-08-03");
  await page.getByLabel("End (exclusive)").fill("2026-09-16");
  await page.getByRole("button", { name: "Query" }).click();

  await expect(page.getByText("Partial success")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Raw close price history" })).toBeVisible();

  const statusSection = page.locator(
    'section[aria-labelledby="symbol-status-heading"]',
  );
  await expect(statusSection.getByText("AAPL", { exact: true })).toBeVisible();
  await expect(statusSection.getByText("MSFT", { exact: true })).toBeVisible();
  await expect(statusSection.getByText("NODATA", { exact: true })).toBeVisible();
  await expect(statusSection.getByText("No data")).toBeVisible();

  await expect(
    page.getByRole("heading", { name: "AAPL candlestick detail" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "AAPL candlestick and volume chart" }),
  ).toBeVisible();

  await page.getByRole("button", { name: /MSFT.*View candlestick detail/i }).click();
  await expect(
    page.getByRole("heading", { name: "MSFT candlestick detail" }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: "MSFT candlestick and volume chart" }),
  ).toBeVisible();
});

test("market explorer primary query controls are keyboard reachable at mobile width", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await loginSampleUser(page);
  await page.getByRole("link", { name: "Market data" }).first().click();

  const symbols = page.getByLabel("Ticker symbols");
  const start = page.getByLabel("Start");
  const end = page.getByLabel("End (exclusive)");
  const query = page.getByRole("button", { name: "Query" });

  await symbols.focus();
  await expect(symbols).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(start).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(end).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(query).toBeFocused();
});
