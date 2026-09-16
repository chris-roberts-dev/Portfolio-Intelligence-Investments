import { expect, type Page } from "@playwright/test";

export const SAMPLE_EMAIL = "sample.portfolio@example.test";
export const SAMPLE_PASSWORD = "local-demo-password";
export const SAMPLE_PORTFOLIO_NAME = "Deterministic Sample Portfolio";
export const SAMPLE_BROWSER_TIME = new Date("2026-09-16T16:00:00Z");

export async function loginSampleUser(page: Page): Promise<void> {
  // The backend demo clock is fixed to the same instant. Freezing browser time
  // keeps frontend range construction deterministic when the suite is run in
  // the future rather than coupling sample coverage to the workstation clock.
  await page.clock.setFixedTime(SAMPLE_BROWSER_TIME);

  await page.goto("/login");
  await page.getByLabel("Email").fill(SAMPLE_EMAIL);
  await page.getByLabel("Password").fill(SAMPLE_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
}

export async function openSampleDashboard(page: Page): Promise<void> {
  const card = page.getByRole("article").filter({
    has: page.getByRole("heading", { name: SAMPLE_PORTFOLIO_NAME }),
  });
  await card.getByRole("link", { name: /Open dashboard/ }).click();
  await expect(page.getByText("Portfolio performance")).toBeVisible();
}
