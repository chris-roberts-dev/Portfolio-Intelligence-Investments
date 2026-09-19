import {
  expect,
  test,
  type Locator,
  type Page,
} from "@playwright/test";

import { loginSampleUser } from "./support";

async function tabUntilFocused(
  page: Page,
  target: Locator,
  maxTabs = 6,
): Promise<void> {
  for (let attempt = 0; attempt < maxTabs; attempt += 1) {
    const focused = await target.evaluate(
      (element) => element === document.activeElement,
    );

    if (focused) {
      return;
    }

    await page.keyboard.press("Tab");
  }

  await expect(target).toBeFocused();
}

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
  await expect(
    page.getByRole("heading", {
      name: "Raw close price history",
    }),
  ).toBeVisible();

  const statusSection = page.locator(
    'section[aria-labelledby="symbol-status-heading"]',
  );

  await expect(
    statusSection.getByText("AAPL", {
      exact: true,
    }),
  ).toBeVisible();

  await expect(
    statusSection.getByText("MSFT", {
      exact: true,
    }),
  ).toBeVisible();

  await expect(
    statusSection.getByText("NODATA", {
      exact: true,
    }),
  ).toBeVisible();

  await expect(
    statusSection.getByText("No data"),
  ).toBeVisible();

  await expect(
    page.getByRole("heading", {
      name: "AAPL candlestick detail",
    }),
  ).toBeVisible();

  await expect(
    page.getByRole("img", {
      name: /AAPL daily OHLC candlesticks with volume/i,
    }),
  ).toBeVisible();

  await page
    .getByRole("button", {
      name: /MSFT.*View candlestick detail/i,
    })
    .click();

  await expect(
    page.getByRole("heading", {
      name: "MSFT candlestick detail",
    }),
  ).toBeVisible();

  await expect(
    page.getByRole("img", {
      name: /MSFT daily OHLC candlesticks with volume/i,
    }),
  ).toBeVisible();
});

test("market explorer primary query controls are keyboard reachable at mobile width", async ({
  page,
}) => {
  await page.setViewportSize({
    width: 360,
    height: 800,
  });

  await loginSampleUser(page);

  // This test is about the query controls, not the responsive navigation
  // drawer. Navigate directly so the hidden desktop sidebar cannot become a
  // false prerequisite for the accessibility assertion.
  await page.goto("/market-data");

  const symbols = page.getByLabel("Ticker symbols");
  const start = page.getByLabel("Start");
  const end = page.getByLabel("End (exclusive)");
  const query = page.getByRole("button", {
    name: "Query",
  });

  await symbols.focus();
  await expect(symbols).toBeFocused();

  await tabUntilFocused(page, start);
  await expect(start).toBeFocused();

  await tabUntilFocused(page, end);
  await expect(end).toBeFocused();

  await tabUntilFocused(page, query);
  await expect(query).toBeFocused();
});
