import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "cd ../backend && " +
        "uv run python manage.py migrate --noinput --settings=config.settings.demo && " +
        "uv run python manage.py flush --noinput --settings=config.settings.demo && " +
        "uv run python manage.py seed_sample_portfolio --reset --settings=config.settings.demo && " +
        "uv run python manage.py runserver 127.0.0.1:8000 --noreload --settings=config.settings.demo",
      url: "http://127.0.0.1:8000/api/v1/health/",
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173/login",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        VITE_DEV_API_PROXY_TARGET: "http://127.0.0.1:8000",
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
