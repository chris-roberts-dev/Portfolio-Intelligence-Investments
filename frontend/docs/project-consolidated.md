# Project Codebase Reference

> This document was automatically generated from the project source tree. Each section contains the original relative file path followed by the complete contents of that file.

This document is intended to provide ChatGPT, Claude, or another AI coding assistant with repository context.

---

# File Index

Files included: **56**

```text
.dockerignore
Dockerfile
index.html
package.json
src/api/auth.test.ts
src/api/auth.ts
src/api/client.ts
src/api/portfolios.test.ts
src/api/portfolios.ts
src/App.test.tsx
src/App.tsx
src/components/charts/AllocationChart.tsx
src/components/charts/chartTheme.ts
src/components/charts/HoldingSparkline.tsx
src/components/charts/PerformanceChart.tsx
src/components/ui/DashboardCard.tsx
src/components/ui/DataQualityBadge.tsx
src/components/ui/LazySection.test.tsx
src/components/ui/LazySection.tsx
src/components/ui/Skeleton.tsx
src/components/ui/StatePanel.tsx
src/features/auth/ProtectedRoute.tsx
src/features/dashboard/AllocationPanel.test.tsx
src/features/dashboard/AllocationPanel.tsx
src/features/dashboard/DashboardOverview.test.tsx
src/features/dashboard/DashboardOverview.tsx
src/features/dashboard/dateRange.test.ts
src/features/dashboard/dateRange.ts
src/features/dashboard/formatting.ts
src/features/dashboard/HoldingsPanel.test.tsx
src/features/dashboard/HoldingsPanel.tsx
src/features/dashboard/MoversPanel.test.tsx
src/features/dashboard/MoversPanel.tsx
src/features/dashboard/PerformanceHero.tsx
src/features/dashboard/PortfolioSummaryCard.tsx
src/features/dashboard/ReviewItemsPanel.test.tsx
src/features/dashboard/ReviewItemsPanel.tsx
src/hooks/useAuth.ts
src/hooks/usePortfolioData.ts
src/index.css
src/layouts/DashboardShell.tsx
src/main.tsx
src/pages/DashboardPage.test.tsx
src/pages/DashboardPage.tsx
src/pages/HoldingDetailPage.test.tsx
src/pages/HoldingDetailPage.tsx
src/pages/HomePage.tsx
src/pages/LoginPage.test.tsx
src/pages/LoginPage.tsx
src/pages/PortfolioAnalysisPage.test.tsx
src/pages/PortfolioAnalysisPage.tsx
src/test/setup.ts
src/types/analytics.ts
src/types/dashboard.ts
tsconfig.json
vite.config.ts
```

---

# File: `.dockerignore`

````text
node_modules/
dist/
coverage/

.env
.env.*

.git/
.gitignore

npm-debug.log*
*.log
````

---

# File: `Dockerfile`

````dockerfile
FROM node:24.21.0-bookworm-slim

WORKDIR /app

RUN npm install --global npm@11.19.0

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
````

---

# File: `index.html`

````html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta
      name="description"
      content="Portfolio Intelligence investment analytics and decision-support platform."
    />
    <title>Portfolio Intelligence</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
````

---

# File: `package.json`

````json
{
  "name": "portfolio-intelligence-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "packageManager": "npm@11.19.0",
  "engines": {
    "node": "24.21.0",
    "npm": "11.19.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "npm run typecheck && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@tanstack/react-query": "5.102.8",
    "echarts": "6.1.0",
    "react": "19.2.8",
    "react-dom": "19.2.8",
    "react-router": "8.3.1"
  },
  "devDependencies": {
    "@tailwindcss/vite": "4.3.3",
    "@testing-library/dom": "10.4.1",
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.3",
    "@types/node": "24.13.3",
    "@types/react": "19.2.17",
    "@types/react-dom": "19.2.3",
    "@vitejs/plugin-react": "6.0.4",
    "jsdom": "30.0.1",
    "tailwindcss": "4.3.3",
    "typescript": "6.0.2",
    "vite": "8.1.5",
    "vitest": "5.0.0"
  }
}
````

---

# File: `src/api/auth.test.ts`

````typescript
import {
  fetchAuthSession,
  loginWithPassword,
  logoutSession,
} from "./auth";

beforeEach(() => {
  document.cookie = "csrftoken=test-csrf-token; path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("session authentication API", () => {
  it("boots the current session with credentials included", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({
          authenticated: false,
          user: null,
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuthSession();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/session/",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );
  });

  it("sends JSON credentials and the CSRF cookie on login", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({
          authenticated: true,
          user: {
            id: "00000000-0000-0000-0000-000000000001",
            email: "owner@example.com",
            first_name: "Portfolio",
            last_name: "Owner",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loginWithPassword({
      email: "owner@example.com",
      password: "secret-password",
    });

    const [, request] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers(request?.headers);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/auth/login/");
    expect(request?.method).toBe("POST");
    expect(request?.credentials).toBe("include");
    expect(headers.get("X-CSRFToken")).toBe("test-csrf-token");
    expect(request?.body).toBe(
      JSON.stringify({
        email: "owner@example.com",
        password: "secret-password",
      }),
    );
  });

  it("sends the current CSRF token when logging out", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({
          authenticated: false,
          user: null,
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await logoutSession();

    const [, request] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers(request?.headers);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/auth/logout/");
    expect(request?.method).toBe("POST");
    expect(headers.get("X-CSRFToken")).toBe("test-csrf-token");
  });
});
````

---

# File: `src/api/auth.ts`

````typescript
import { apiGet, apiPost } from "./client";

export interface AuthenticatedUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface AuthSessionResult {
  authenticated: boolean;
  user: AuthenticatedUser | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export function fetchAuthSession(signal?: AbortSignal): Promise<AuthSessionResult> {
  return apiGet<AuthSessionResult>("/api/v1/auth/session/", { signal });
}

export function loginWithPassword(
  request: LoginRequest,
  signal?: AbortSignal,
): Promise<AuthSessionResult> {
  return apiPost<AuthSessionResult, LoginRequest>(
    "/api/v1/auth/login/",
    request,
    { signal },
  );
}

export function logoutSession(signal?: AbortSignal): Promise<AuthSessionResult> {
  return apiPost<AuthSessionResult, Record<string, never>>(
    "/api/v1/auth/logout/",
    {},
    { signal },
  );
}
````

---

# File: `src/api/client.ts`

````typescript
interface ApiErrorPayload {
  code?: unknown;
  detail?: unknown;
  errors?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly payload: unknown;

  constructor(
    message: string,
    options: { status: number; code: string | null; payload: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.payload = options.payload;
  }
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!configured) {
    return "";
  }

  return configured.endsWith("/") ? configured.slice(0, -1) : configured;
}

function csrfTokenFromCookie(): string | null {
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("csrftoken="));

  if (!cookie) {
    return null;
  }

  const value = cookie.slice("csrftoken=".length);
  return value ? decodeURIComponent(value) : null;
}

function errorMessage(payload: ApiErrorPayload, response: Response): string {
  if (typeof payload.detail === "string" && payload.detail.length > 0) {
    return payload.detail;
  }

  if (typeof payload.code === "string" && payload.code.length > 0) {
    return payload.code.replaceAll("_", " ").toLowerCase();
  }

  return `Request failed with status ${response.status}.`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const errorPayload =
      payload !== null && typeof payload === "object"
        ? (payload as ApiErrorPayload)
        : {};

    throw new ApiError(errorMessage(errorPayload, response), {
      status: response.status,
      code: typeof errorPayload.code === "string" ? errorPayload.code : null,
      payload,
    });
  }

  return payload as T;
}

export async function apiGet<T>(
  path: string,
  options: { signal?: AbortSignal } = {},
): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    signal: options.signal,
  });

  return parseResponse<T>(response);
}

export async function apiPost<T, TBody extends object>(
  path: string,
  body: TBody,
  options: { signal?: AbortSignal } = {},
): Promise<T> {
  const csrfToken = csrfTokenFromCookie();
  const headers = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });

  if (csrfToken !== null) {
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify(body),
    signal: options.signal,
  });

  return parseResponse<T>(response);
}
````

---

# File: `src/api/portfolios.test.ts`

````typescript
import {
  fetchDashboardSnapshot,
  fetchPortfolioAnalytics,
} from "./portfolios";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("portfolio read APIs", () => {
  it("requests the canonical owner-scoped snapshot with explicit range inputs", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            snapshot: {
              snapshot_id: "00000000-0000-0000-0000-000000000001",
            },
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardSnapshot({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-09-01",
      end: "2026-09-16",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/portfolios/00000000-0000-0000-0000-000000000002/dashboard/?start=2026-09-01&end=2026-09-16",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );
  });

  it("requests portfolio analytics with explicit range and user-selected rolling window only", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            portfolio_id: "00000000-0000-0000-0000-000000000002",
            observations: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchPortfolioAnalytics({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-03-16",
      end: "2026-09-17",
      rollingWindow: 21,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/analytics/portfolios/00000000-0000-0000-0000-000000000002/?start=2026-03-16&end=2026-09-17&rolling_window=21",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );

    const requestedUrl = String(fetchMock.mock.calls[0]?.[0]);

    expect(requestedUrl).not.toContain("risk_free_rate_annual");
    expect(requestedUrl).not.toContain(
      "minimum_acceptable_return_annual",
    );
  });

  it("does not send a hidden rolling-return window", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            portfolio_id: "00000000-0000-0000-0000-000000000002",
            observations: 0,
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchPortfolioAnalytics({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-03-16",
      end: "2026-09-17",
    });

    const requestedUrl = String(fetchMock.mock.calls[0]?.[0]);

    expect(requestedUrl).not.toContain("rolling_window");
    expect(requestedUrl).not.toContain("risk_free_rate_annual");
    expect(requestedUrl).not.toContain(
      "minimum_acceptable_return_annual",
    );
  });
});
````

---

# File: `src/api/portfolios.ts`

````typescript
import type { PortfolioAnalyticsResult } from "../types/analytics";
import type {
  DashboardSnapshotResult,
  PortfolioListItem,
} from "../types/dashboard";
import { apiGet } from "./client";

export interface DashboardSnapshotRequest {
  portfolioId: string;
  start: string;
  end: string;
}

export interface PortfolioAnalyticsRequest {
  portfolioId: string;
  start: string;
  end: string;
  rollingWindow?: number;
}

export function fetchPortfolios(
  signal?: AbortSignal,
): Promise<PortfolioListItem[]> {
  return apiGet<PortfolioListItem[]>("/api/v1/portfolios/", { signal });
}

export function fetchDashboardSnapshot(
  request: DashboardSnapshotRequest,
  signal?: AbortSignal,
): Promise<DashboardSnapshotResult> {
  const params = new URLSearchParams({
    start: request.start,
    end: request.end,
  });
  const portfolioId = encodeURIComponent(request.portfolioId);

  return apiGet<DashboardSnapshotResult>(
    `/api/v1/portfolios/${portfolioId}/dashboard/?${params.toString()}`,
    { signal },
  );
}

export function fetchPortfolioAnalytics(
  request: PortfolioAnalyticsRequest,
  signal?: AbortSignal,
): Promise<PortfolioAnalyticsResult> {
  const params = new URLSearchParams({
    start: request.start,
    end: request.end,
  });

  if (request.rollingWindow !== undefined) {
    params.set("rolling_window", String(request.rollingWindow));
  }

  const portfolioId = encodeURIComponent(request.portfolioId);

  return apiGet<PortfolioAnalyticsResult>(
    `/api/v1/analytics/portfolios/${portfolioId}/?${params.toString()}`,
    { signal },
  );
}
````

---

# File: `src/App.test.tsx`

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { App } from "./App";

function renderApp(initialEntry = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App authentication routing", () => {
  it("redirects an anonymous protected route to sign in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ authenticated: false, user: null }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        ),
      ),
    );

    renderApp("/portfolios/portfolio-1/dashboard?range=1M");

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("renders protected portfolio content for an authenticated session", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/v1/auth/session/")) {
        return new Response(
          JSON.stringify({
            authenticated: true,
            user: {
              id: "00000000-0000-0000-0000-000000000001",
              email: "owner@example.com",
              first_name: "Portfolio",
              last_name: "Owner",
            },
          }),
          {
            status: 200,
            headers: { "content-type": "application/json" },
          },
        );
      }

      if (url.endsWith("/api/v1/portfolios/")) {
        return new Response(JSON.stringify([]), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderApp();

    expect(
      await screen.findByRole("heading", { name: "Select a portfolio" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" }),
    ).toBeInTheDocument();
  });
});
````

---

# File: `src/App.tsx`

````tsx
import { Route, Routes } from "react-router";

import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { DashboardPage } from "./pages/DashboardPage";
import { HoldingDetailPage } from "./pages/HoldingDetailPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { PortfolioAnalysisPage } from "./pages/PortfolioAnalysisPage";

function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="max-w-md text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-700">
          404
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
          Page not found
        </h1>
        <p className="mt-3 text-slate-600">
          The requested Portfolio Intelligence route does not exist.
        </p>
      </div>
    </main>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<HomePage />} />

        <Route
          path="/portfolios/:portfolioId/dashboard"
          element={<DashboardPage />}
        />

        <Route
          path="/portfolios/:portfolioId/analysis"
          element={<PortfolioAnalysisPage />}
        />

        <Route
          path="/portfolios/:portfolioId/holdings/:assetId"
          element={<HoldingDetailPage />}
        />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
````

---

# File: `src/components/charts/AllocationChart.tsx`

````tsx
import type { EChartsOption } from "echarts";
import { BarChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import { formatCurrency } from "../../features/dashboard/formatting";
import type { DashboardAllocationGroup } from "../../types/dashboard";
import { chartTheme } from "./chartTheme";

echarts.use([
  BarChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

const ALLOCATION_COLORS = [
  "#2563eb",
  "#0f766e",
  "#7c3aed",
  "#d97706",
  "#475569",
] as const;

interface AllocationChartProps {
  groups: DashboardAllocationGroup[];
  currency: string;
}

function formatWeight(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function seriesNameFromParams(params: unknown): string | null {
  const first = Array.isArray(params) ? params[0] : params;

  if (
    first === null ||
    typeof first !== "object" ||
    !("seriesName" in first)
  ) {
    return null;
  }

  return typeof first.seriesName === "string" ? first.seriesName : null;
}

export function AllocationChart({ groups, currency }: AllocationChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const weightedGroups = useMemo(
    () => groups.filter((group) => group.weight !== null),
    [groups],
  );

  useEffect(() => {
    const container = containerRef.current;

    if (container === null || weightedGroups.length === 0) {
      return undefined;
    }

    const chart = echarts.init(container, undefined, {
      renderer: "canvas",
    });
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const option: EChartsOption = {
      animation: !reduceMotion,
      aria: {
        enabled: true,
        decal: {
          show: true,
        },
        description:
          "Current portfolio allocation by backend-authoritative asset class and cash weight.",
      },
      color: [...ALLOCATION_COLORS],
      grid: {
        left: 8,
        right: 8,
        top: 44,
        bottom: 28,
        containLabel: true,
      },
      legend: {
        top: 0,
        left: 0,
        textStyle: {
          color: chartTheme.axisText,
          fontSize: 12,
        },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "shadow",
        },
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: {
          color: chartTheme.tooltipText,
        },
        formatter: (params: unknown) => {
          const seriesName = seriesNameFromParams(params);
          const group = weightedGroups.find(
            (candidate) => candidate.label === seriesName,
          );

          if (group === undefined) {
            return "";
          }

          return [
            `<strong>${escapeHtml(group.label)}</strong>`,
            escapeHtml(formatCurrency(group.market_value, currency)),
            escapeHtml(formatWeight(group.weight)),
          ].join("<br />");
        },
      },
      xAxis: {
        type: "value",
        min: 0,
        max: 1,
        axisLabel: {
          color: chartTheme.axisText,
          formatter: (value: string | number) =>
            `${Math.round(Number(value) * 100)}%`,
        },
        splitLine: {
          lineStyle: {
            color: chartTheme.gridline,
          },
        },
      },
      yAxis: {
        type: "category",
        data: ["Portfolio"],
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { show: false },
      },
      series: weightedGroups.map((group, index) => ({
        name: group.label,
        type: "bar" as const,
        stack: "allocation",
        barWidth: 34,
        data: [group.weight],
        itemStyle: {
          color: ALLOCATION_COLORS[index % ALLOCATION_COLORS.length],
          borderRadius:
            index === 0
              ? [8, 0, 0, 8]
              : index === weightedGroups.length - 1
                ? [0, 8, 8, 0]
                : 0,
        },
        emphasis: {
          focus: "series" as const,
        },
      })),
    };

    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [currency, weightedGroups]);

  if (weightedGroups.length === 0) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="h-40 w-full"
      role="img"
      aria-label="Portfolio allocation chart"
    />
  );
}
````

---

# File: `src/components/charts/chartTheme.ts`

````typescript
export const chartTheme = {
  primary: "#2563eb",
  benchmark: "#64748b",
  gridline: "#e2e8f0",
  axisText: "#64748b",
  tooltipBackground: "#0f172a",
  tooltipText: "#f8fafc",
} as const;
````

---

# File: `src/components/charts/HoldingSparkline.tsx`

````tsx
import { LineChart } from "echarts/charts";
import { AriaComponent, GridComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import { chartTheme } from "./chartTheme";
import { formatCurrency, formatDate } from "../../features/dashboard/formatting";
import type { HoldingSparklinePoint } from "../../types/dashboard";

echarts.use([
  LineChart,
  AriaComponent,
  GridComponent,
  CanvasRenderer,
]);

interface HoldingSparklineProps {
  points: HoldingSparklinePoint[];
  symbol: string;
  currency: string;
}

interface SparklineRow {
  date: string;
  value: number | null;
}

function toFiniteNumber(value: string | null): number | null {
  if (value === null) {
    return null;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function sparklineSummary(
  rows: SparklineRow[],
  symbol: string,
  currency: string,
): string {
  const available = rows.filter(
    (row): row is SparklineRow & { value: number } => row.value !== null,
  );
  const missingCount = rows.length - available.length;

  if (available.length === 0) {
    return `${symbol} has no selected-period sparkline prices.`;
  }

  const first = available[0];
  const last = available[available.length - 1];

  if (!first || !last) {
    return `${symbol} selected-period sparkline data is unavailable.`;
  }

  const missingText =
    missingCount > 0
      ? ` ${missingCount} trading-session observation${missingCount === 1 ? " is" : "s are"} missing and not interpolated.`
      : "";

  return `${symbol} adjusted close moved from ${formatCurrency(
    String(first.value),
    currency,
  )} on ${formatDate(first.date)} to ${formatCurrency(
    String(last.value),
    currency,
  )} on ${formatDate(last.date)}.${missingText}`;
}

export function HoldingSparkline({
  points,
  symbol,
  currency,
}: HoldingSparklineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rows = useMemo<SparklineRow[]>(
    () =>
      points.map((point) => ({
        date: point.observation_date,
        value: toFiniteNumber(point.adjusted_close),
      })),
    [points],
  );
  const summary = useMemo(
    () => sparklineSummary(rows, symbol, currency),
    [currency, rows, symbol],
  );

  useEffect(() => {
    const container = containerRef.current;

    if (container === null || rows.length === 0) {
      return undefined;
    }

    const chart = echarts.init(container);
    const reduceMotion =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

    chart.setOption({
      animation: !reduceMotion,
      aria: {
        enabled: true,
        description: summary,
      },
      grid: {
        left: 1,
        right: 1,
        top: 3,
        bottom: 3,
      },
      xAxis: {
        type: "time",
        show: false,
      },
      yAxis: {
        type: "value",
        show: false,
        scale: true,
      },
      series: [
        {
          type: "line" as const,
          showSymbol: false,
          connectNulls: false,
          smooth: false,
          silent: true,
          lineStyle: {
            width: 1.75,
            color: chartTheme.primary,
          },
          data: rows.map((row) => [row.date, row.value]),
        },
      ],
    });

    const resize = () => chart.resize();
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(resize);

    observer?.observe(container);
    window.addEventListener("resize", resize);

    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [rows, summary]);

  if (rows.length === 0) {
    return (
      <span className="text-xs text-slate-500">
        No history
      </span>
    );
  }

  return (
    <div className="min-w-0">
      <div
        ref={containerRef}
        className="h-12 w-full min-w-24"
        role="img"
        aria-label={summary}
      />
      <span className="sr-only">{summary}</span>
    </div>
  );
}
````

---

# File: `src/components/charts/PerformanceChart.tsx`

````tsx
import type { EChartsOption } from "echarts";
import { LineChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import { formatCurrency, formatDate, formatPercent } from "../../features/dashboard/formatting";
import type { DashboardPerformanceResult } from "../../types/dashboard";
import { chartTheme } from "./chartTheme";

export type PerformanceChartMode = "VALUE" | "RETURN";

echarts.use([
  LineChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface PerformanceChartProps {
  performance: DashboardPerformanceResult;
  currency: string;
  mode: PerformanceChartMode;
}

interface ChartRow {
  date: string;
  portfolioValue: number | null;
  portfolioReturn: number | null;
  benchmarkReturn: number | null;
  quality: string;
}

function toFiniteNumber(value: string | null): number | null {
  if (value === null) {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function PerformanceChart({
  performance,
  currency,
  mode,
}: PerformanceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rows = useMemo<ChartRow[]>(() => {
    const benchmarkByDate = new Map(
      performance.benchmark_points.map((point) => [
        point.observation_date,
        point.cumulative_return,
      ]),
    );

    return performance.points.map((point) => ({
      date: point.observation_date,
      portfolioValue: toFiniteNumber(point.portfolio_value),
      portfolioReturn: point.cumulative_return,
      benchmarkReturn: benchmarkByDate.get(point.observation_date) ?? null,
      quality: point.data_quality,
    }));
  }, [performance]);

  useEffect(() => {
    const container = containerRef.current;

    if (container === null || rows.length === 0) {
      return undefined;
    }

    const chart = echarts.init(container);
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const isReturnMode = mode === "RETURN";
    const portfolioData = rows.map((row) => [
      row.date,
      isReturnMode ? row.portfolioReturn : row.portfolioValue,
    ]);
    const benchmarkData = rows.map((row) => [row.date, row.benchmarkReturn]);

    const option: EChartsOption = {
      animation: !reduceMotion,
      aria: {
        enabled: true,
        description: isReturnMode
          ? "Portfolio cumulative return over the selected period."
          : "Portfolio market value over the selected period.",
      },
      grid: {
        left: 12,
        right: 18,
        top: isReturnMode && performance.benchmark_points.length > 0 ? 42 : 20,
        bottom: 16,
        containLabel: true,
      },
      legend: {
        show: isReturnMode && performance.benchmark_points.length > 0,
        top: 0,
        right: 0,
        textStyle: { color: chartTheme.axisText },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: { color: chartTheme.tooltipText },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) {
            return "";
          }

          const first = params[0] as { data?: unknown };
          const pair = Array.isArray(first.data) ? first.data : [];
          const date = typeof pair[0] === "string" ? pair[0] : "";
          const row = rows.find((candidate) => candidate.date === date);

          if (!row) {
            return "";
          }

          const portfolioLabel = isReturnMode
            ? formatPercent(row.portfolioReturn)
            : formatCurrency(
                row.portfolioValue === null ? null : String(row.portfolioValue),
                currency,
              );
          const benchmarkLabel =
            isReturnMode && row.benchmarkReturn !== null
              ? `<br/>Benchmark: ${formatPercent(row.benchmarkReturn)}`
              : "";

          return `${formatDate(row.date)}<br/>Portfolio: ${portfolioLabel}${benchmarkLabel}<br/>Data: ${row.quality}`;
        },
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: chartTheme.gridline } },
        axisLabel: { color: chartTheme.axisText },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        scale: true,
        axisLabel: {
          color: chartTheme.axisText,
          formatter: (value: number) =>
            isReturnMode
              ? `${(value * 100).toFixed(0)}%`
              : new Intl.NumberFormat(undefined, {
                  notation: "compact",
                  maximumFractionDigits: 1,
                }).format(value),
        },
        splitLine: {
          lineStyle: { color: chartTheme.gridline },
        },
      },
      series: [
        {
          name: "Portfolio",
          type: "line",
          showSymbol: false,
          connectNulls: false,
          smooth: false,
          lineStyle: { width: 2.5, color: chartTheme.primary },
          itemStyle: { color: chartTheme.primary },
          areaStyle: isReturnMode
            ? undefined
            : { color: "rgba(37, 99, 235, 0.08)" },
          data: portfolioData,
        },
        ...(isReturnMode && performance.benchmark_points.length > 0
          ? [
              {
                name: performance.provenance.benchmark_symbol ?? "Benchmark",
                type: "line" as const,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {
                  width: 1.75,
                  type: "dashed" as const,
                  color: chartTheme.benchmark,
                },
                itemStyle: { color: chartTheme.benchmark },
                data: benchmarkData,
              },
            ]
          : []),
      ],
    };
    chart.setOption(option);

    const resize = () => chart.resize();
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(resize);

    observer?.observe(container);
    window.addEventListener("resize", resize);

    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [currency, mode, performance, rows]);

  if (rows.length === 0) {
    return null;
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-72 w-full sm:h-80"
        role="img"
        tabIndex={0}
        aria-label={
          mode === "RETURN"
            ? "Portfolio cumulative return chart"
            : "Portfolio market value chart"
        }
      />

      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          View chart data
        </summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">Date</th>
                <th className="py-2 pr-4 font-semibold">Portfolio value</th>
                <th className="py-2 pr-4 font-semibold">Portfolio return</th>
                <th className="py-2 pr-4 font-semibold">Benchmark return</th>
                <th className="py-2 font-semibold">Quality</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.date} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-4 text-slate-700">{formatDate(row.date)}</td>
                  <td className="py-2 pr-4 text-slate-700">
                    {formatCurrency(
                      row.portfolioValue === null ? null : String(row.portfolioValue),
                      currency,
                    )}
                  </td>
                  <td className="py-2 pr-4 text-slate-700">
                    {formatPercent(row.portfolioReturn)}
                  </td>
                  <td className="py-2 pr-4 text-slate-700">
                    {formatPercent(row.benchmarkReturn)}
                  </td>
                  <td className="py-2 text-slate-700">{row.quality}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
````

---

# File: `src/components/ui/DashboardCard.tsx`

````tsx
import type { PropsWithChildren, ReactNode } from "react";

interface DashboardCardProps extends PropsWithChildren {
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
  className?: string;
}

export function DashboardCard({
  title,
  eyebrow,
  actions,
  className = "",
  children,
}: DashboardCardProps) {
  return (
    <section
      className={`rounded-3xl border border-slate-200 bg-white shadow-sm ${className}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-5 py-5 sm:px-6">
        <div>
          {eyebrow ? (
            <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              {eyebrow}
            </p>
          ) : null}
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            {title}
          </h2>
        </div>
        {actions}
      </header>
      <div className="px-5 py-5 sm:px-6 sm:py-6">{children}</div>
    </section>
  );
}
````

---

# File: `src/components/ui/DataQualityBadge.tsx`

````tsx
import type { PerformanceDataQuality } from "../../types/dashboard";

const QUALITY_STYLES: Record<PerformanceDataQuality, string> = {
  CURRENT: "border-emerald-200 bg-emerald-50 text-emerald-800",
  STALE: "border-amber-200 bg-amber-50 text-amber-900",
  PARTIAL: "border-orange-200 bg-orange-50 text-orange-900",
  UNAVAILABLE: "border-rose-200 bg-rose-50 text-rose-900",
};

const QUALITY_LABELS: Record<PerformanceDataQuality, string> = {
  CURRENT: "Current",
  STALE: "Stale data",
  PARTIAL: "Partial data",
  UNAVAILABLE: "Unavailable",
};

export function DataQualityBadge({
  quality,
}: {
  quality: PerformanceDataQuality;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${QUALITY_STYLES[quality]}`}
    >
      {QUALITY_LABELS[quality]}
    </span>
  );
}
````

---

# File: `src/components/ui/LazySection.test.tsx`

````tsx
import { act, render, screen } from "@testing-library/react";

import { LazySection } from "./LazySection";

describe("LazySection", () => {
  it("defers lower-page content until it approaches the viewport", () => {
    let callback: IntersectionObserverCallback | null = null;
    const observe = vi.fn();
    const disconnect = vi.fn();

    class MockIntersectionObserver {
      root = null;
      rootMargin = "320px 0px";
      thresholds = [0];

      constructor(nextCallback: IntersectionObserverCallback) {
        callback = nextCallback;
      }

      observe = observe;
      unobserve = vi.fn();
      disconnect = disconnect;
      takeRecords = vi.fn(() => []);
    }

    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);

    render(
      <LazySection fallback={<div>Deferred holdings</div>}>
        <div>Loaded holdings</div>
      </LazySection>,
    );

    expect(screen.getByText("Deferred holdings")).toBeInTheDocument();
    expect(screen.queryByText("Loaded holdings")).not.toBeInTheDocument();
    expect(observe).toHaveBeenCalledTimes(1);

    act(() => {
      callback?.(
        [
          {
            isIntersecting: true,
          } as IntersectionObserverEntry,
        ],
        {} as IntersectionObserver,
      );
    });

    expect(screen.getByText("Loaded holdings")).toBeInTheDocument();
    expect(disconnect).toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});
````

---

# File: `src/components/ui/LazySection.tsx`

````tsx
import {
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
  type ReactNode,
} from "react";

interface LazySectionProps extends PropsWithChildren {
  fallback: ReactNode;
  rootMargin?: string;
}

export function LazySection({
  fallback,
  rootMargin = "320px 0px",
  children,
}: LazySectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(
    () => typeof IntersectionObserver === "undefined",
  );

  useEffect(() => {
    if (isVisible || typeof IntersectionObserver === "undefined") {
      return undefined;
    }

    const container = containerRef.current;

    if (container === null) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );

    observer.observe(container);

    return () => observer.disconnect();
  }, [isVisible, rootMargin]);

  return (
    <div ref={containerRef}>
      {isVisible ? children : fallback}
    </div>
  );
}
````

---

# File: `src/components/ui/Skeleton.tsx`

````tsx
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-xl bg-slate-200 ${className}`}
    />
  );
}
````

---

# File: `src/components/ui/StatePanel.tsx`

````tsx
import type { ReactNode } from "react";

interface StatePanelProps {
  title: string;
  message: string;
  action?: ReactNode;
  tone?: "neutral" | "error";
}

export function StatePanel({
  title,
  message,
  action,
  tone = "neutral",
}: StatePanelProps) {
  const toneClass =
    tone === "error"
      ? "border-rose-200 bg-rose-50 text-rose-950"
      : "border-slate-200 bg-slate-50 text-slate-900";

  return (
    <div
      className={`rounded-2xl border p-5 ${toneClass}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-1 text-sm leading-6 opacity-80">{message}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
````

---

# File: `src/features/auth/ProtectedRoute.tsx`

````tsx
import { Navigate, Outlet, useLocation } from "react-router";

import { StatePanel } from "../../components/ui/StatePanel";
import { useSession } from "../../hooks/useAuth";

export function ProtectedRoute() {
  const location = useLocation();
  const sessionQuery = useSession();

  if (sessionQuery.isPending) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div
          role="status"
          aria-label="Checking authentication"
          className="h-12 w-12 animate-pulse rounded-2xl bg-slate-200"
        />
      </main>
    );
  }

  if (sessionQuery.error instanceof Error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
        <div className="w-full max-w-xl">
          <StatePanel
            title="Session could not be checked"
            message={sessionQuery.error.message}
            tone="error"
            action={
              <button
                type="button"
                onClick={() => void sessionQuery.refetch()}
                className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
              >
                Retry
              </button>
            }
          />
        </div>
      </main>
    );
  }

  if (!sessionQuery.data?.authenticated) {
    const from = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to="/login" replace state={{ from }} />;
  }

  return <Outlet />;
}
````

---

# File: `src/features/dashboard/AllocationPanel.test.tsx`

````tsx
import { render, screen } from "@testing-library/react";

import type { DashboardAllocationResult } from "../../types/dashboard";
import { AllocationPanel } from "./AllocationPanel";

vi.mock("../../components/charts/AllocationChart", () => ({
  AllocationChart: () => <div data-testid="allocation-chart">Allocation chart</div>,
}));

function allocationFixture(): DashboardAllocationResult {
  return {
    allocation_available: true,
    groups: [
      {
        key: "STOCK",
        label: "Stocks",
        is_cash: false,
        asset_count: 2,
        market_value: "600.00",
        weight: 0.6,
      },
      {
        key: "ETF",
        label: "ETFs",
        is_cash: false,
        asset_count: 1,
        market_value: "300.00",
        weight: 0.3,
      },
      {
        key: "CASH",
        label: "Cash",
        is_cash: true,
        asset_count: 0,
        market_value: "100.00",
        weight: 0.1,
      },
    ],
    totals: {
      total_market_value: "1000.00",
      invested_value: "900.00",
      cash_value: "100.00",
      invested_weight: 0.9,
      cash_weight: 0.1,
    },
    data_quality: "CURRENT",
    unavailable_reason: null,
    warnings: [],
    provenance: {
      portfolio_id: "00000000-0000-0000-0000-000000000002",
      base_currency: "USD",
      provider: "mock",
      as_of: "2026-09-15T22:00:00Z",
      data_as_of: "2026-09-15T21:55:00Z",
      calculated_at: "2026-09-15T22:00:00Z",
      price_field: "close",
      grouping_dimension: "ASSET_CLASS",
      supported_grouping_dimensions: ["ASSET_CLASS"],
      grouping_source: "Asset.asset_type",
      ordering_rule: "SECURITY_WEIGHT_DESC_THEN_GROUP_KEY_CASH_LAST_V1",
      other_grouping_applied: false,
      other_grouping_threshold: null,
      other_grouping_rule:
        "No Other aggregation is applied in the MVP because persisted security asset types are exhaustively constrained to STOCK and ETF.",
      weight_sum_tolerance: 1e-8,
    },
  };
}

describe("AllocationPanel", () => {
  it("renders backend-authoritative groups, exact values, and equivalent table data", async () => {
    render(
      <AllocationPanel
        allocation={allocationFixture()}
        currency="USD"
        moduleError={null}
      />,
    );

    expect(screen.getByRole("heading", { name: "Allocation" })).toBeInTheDocument();
    expect(screen.getByText("$900.00")).toBeInTheDocument();
    expect(screen.getAllByText("$100.00").length).toBeGreaterThan(0);
    expect(screen.getByRole("rowheader", { name: "Stocks" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "ETFs" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Cash" })).toBeInTheDocument();
    expect(screen.getByText("60.0%")).toBeInTheDocument();
    expect(screen.getByText("30.0%")).toBeInTheDocument();
    expect(screen.getByText("10.0%")).toBeInTheDocument();
    expect(
      await screen.findByTestId("allocation-chart"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No Other aggregation is applied in the MVP/),
    ).toBeInTheDocument();
  });

  it("keeps stale allocation visible and explicitly labeled", () => {
    const allocation = allocationFixture();
    allocation.data_quality = "STALE";

    render(
      <AllocationPanel
        allocation={allocation}
        currency="USD"
        moduleError={null}
      />,
    );

    expect(screen.getByText("Stale data")).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Stocks" })).toBeInTheDocument();
  });

  it("shows explicit unavailable state without fabricating weights", () => {
    const allocation = allocationFixture();
    allocation.allocation_available = false;
    allocation.data_quality = "PARTIAL";
    allocation.unavailable_reason = "CURRENT_VALUATION_INCOMPLETE";
    allocation.groups = [];
    allocation.totals.total_market_value = null;
    allocation.totals.invested_value = null;
    allocation.totals.invested_weight = null;
    allocation.totals.cash_weight = null;

    render(
      <AllocationPanel
        allocation={allocation}
        currency="USD"
        moduleError={null}
      />,
    );

    expect(screen.getByText("Partial data")).toBeInTheDocument();
    expect(screen.getByText("Allocation weights are not available.")).toBeInTheDocument();
    expect(screen.getByText("Current valuation incomplete")).toBeInTheDocument();
    expect(screen.queryByTestId("allocation-chart")).not.toBeInTheDocument();
  });
});
````

---

# File: `src/features/dashboard/AllocationPanel.tsx`

````tsx
import { Suspense, lazy } from "react";

import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { Skeleton } from "../../components/ui/Skeleton";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardAllocationGroup,
  DashboardAllocationResult,
} from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  humanizeCode,
} from "./formatting";

const AllocationChart = lazy(async () => {
  const module = await import("../../components/charts/AllocationChart");
  return { default: module.AllocationChart };
});

interface AllocationPanelProps {
  allocation: DashboardAllocationResult | null;
  currency: string;
  moduleError: string | null;
}

function formatWeight(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

function groupPositionLabel(group: DashboardAllocationGroup): string {
  if (group.is_cash) {
    return "Cash";
  }

  return `${group.asset_count} ${group.asset_count === 1 ? "holding" : "holdings"}`;
}

function AllocationChartSkeleton() {
  return (
    <div
      className="h-40 rounded-2xl bg-slate-50 p-4"
      role="status"
      aria-label="Loading allocation chart"
    >
      <Skeleton className="h-5 w-48" />
      <Skeleton className="mt-8 h-10 w-full rounded-lg" />
    </div>
  );
}

export function AllocationPanel({
  allocation,
  currency,
  moduleError,
}: AllocationPanelProps) {
  if (moduleError !== null) {
    return (
      <StatePanel
        title="Allocation unavailable"
        message={moduleError}
        tone="error"
      />
    );
  }

  if (allocation === null) {
    return (
      <StatePanel
        title="Allocation unavailable"
        message="No current allocation result is available for this dashboard snapshot."
      />
    );
  }

  const unsupportedReason = humanizeCode(allocation.unavailable_reason);
  const weightedGroups = allocation.groups.filter(
    (group) => group.weight !== null,
  );

  return (
    <section
      className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
      aria-labelledby="allocation-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Current portfolio
          </p>
          <h2
            id="allocation-heading"
            className="mt-1 text-xl font-semibold tracking-tight text-slate-950"
          >
            Allocation
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Backend-authoritative asset-class and cash weights.
          </p>
        </div>
        <DataQualityBadge quality={allocation.data_quality} />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500">Invested value</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatCurrency(allocation.totals.invested_value, currency)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {formatWeight(allocation.totals.invested_weight)} invested
          </p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500">Cash</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatCurrency(allocation.totals.cash_value, currency)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {formatWeight(allocation.totals.cash_weight)} of portfolio
          </p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500">Total value</p>
          <p className="mt-1 text-lg font-semibold text-slate-950">
            {formatCurrency(allocation.totals.total_market_value, currency)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            As of {formatDateTime(allocation.provenance.data_as_of)}
          </p>
        </div>
      </div>

      {!allocation.allocation_available ? (
        <div
          className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          <p className="font-semibold">Allocation weights are not available.</p>
          <p className="mt-1">
            {unsupportedReason ??
              "The backend could not produce authoritative current weights."}
          </p>
        </div>
      ) : null}

      {weightedGroups.length > 0 ? (
        <div className="mt-6">
          <Suspense fallback={<AllocationChartSkeleton />}>
            <AllocationChart groups={allocation.groups} currency={currency} />
          </Suspense>
        </div>
      ) : null}

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[34rem] border-separate border-spacing-0 text-left text-sm">
          <caption className="sr-only">
            Current portfolio allocation by asset class and cash
          </caption>
          <thead>
            <tr className="text-xs uppercase tracking-wide text-slate-500">
              <th scope="col" className="border-b border-slate-200 px-3 py-2 font-semibold">
                Group
              </th>
              <th scope="col" className="border-b border-slate-200 px-3 py-2 font-semibold">
                Positions
              </th>
              <th scope="col" className="border-b border-slate-200 px-3 py-2 text-right font-semibold">
                Market value
              </th>
              <th scope="col" className="border-b border-slate-200 px-3 py-2 text-right font-semibold">
                Weight
              </th>
            </tr>
          </thead>
          <tbody>
            {allocation.groups.map((group) => (
              <tr
                key={group.key}
                data-allocation-group-key={group.key}
                data-market-value={group.market_value}
                data-weight={group.weight ?? undefined}
                className="text-slate-700"
              >
                <th
                  scope="row"
                  className="border-b border-slate-100 px-3 py-3 font-semibold text-slate-950"
                >
                  {group.label}
                </th>
                <td className="border-b border-slate-100 px-3 py-3">
                  {groupPositionLabel(group)}
                </td>
                <td className="border-b border-slate-100 px-3 py-3 text-right font-medium text-slate-950">
                  {formatCurrency(group.market_value, currency)}
                </td>
                <td className="border-b border-slate-100 px-3 py-3 text-right font-medium text-slate-950">
                  {formatWeight(group.weight)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {allocation.warnings.length > 0 ? (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            Allocation notes
          </p>
          <ul className="mt-2 space-y-1 text-sm text-amber-950">
            {allocation.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
        <p>
          Grouping: {allocation.provenance.grouping_dimension.replaceAll("_", " ")} · Source:{" "}
          {allocation.provenance.grouping_source}
        </p>
        <p>
          Supported grouping dimensions:{" "}
          {allocation.provenance.supported_grouping_dimensions.join(", ")}
        </p>
        <p>
          Ordering: {allocation.provenance.ordering_rule} · Price field:{" "}
          {allocation.provenance.price_field}
        </p>
        <p>
          Other grouping: {allocation.provenance.other_grouping_applied ? "Applied" : "Not applied"}
          {allocation.provenance.other_grouping_threshold === null
            ? " · Threshold: none"
            : ` · Threshold: ${allocation.provenance.other_grouping_threshold}`}
        </p>
        <p>{allocation.provenance.other_grouping_rule}</p>
        <p>
          Allocation-to-holdings cross-filtering is not enabled yet. Stable group keys are preserved for a later explicit interaction contract.
        </p>
      </div>
    </section>
  );
}
````

---

# File: `src/features/dashboard/DashboardOverview.test.tsx`

````tsx
import {
  render,
  screen,
} from "@testing-library/react";

import type { DashboardSnapshotResult } from "../../types/dashboard";
import { DashboardOverview } from "./DashboardOverview";

vi.mock(
  "../../components/charts/PerformanceChart",
  () => ({
    PerformanceChart: () => (
      <div data-testid="performance-chart">
        Chart
      </div>
    ),
  }),
);

vi.mock("./AllocationPanel", () => ({
  AllocationPanel: () => (
    <div data-testid="allocation-panel">
      Allocation panel
    </div>
  ),
}));

vi.mock("./HoldingsPanel", () => ({
  HoldingsPanel: () => (
    <div data-testid="holdings-panel">
      Holdings panel
    </div>
  ),
}));

vi.mock("./MoversPanel", () => ({
  MoversPanel: () => (
    <div data-testid="movers-panel">
      Movers panel
    </div>
  ),
}));

vi.mock("./ReviewItemsPanel", () => ({
  ReviewItemsPanel: () => (
    <div data-testid="review-items-panel">
      Review items panel
    </div>
  ),
}));

function snapshotFixture(): DashboardSnapshotResult {
  return {
    snapshot: {
      snapshot_id:
        "00000000-0000-0000-0000-000000000001",
      portfolio_id:
        "00000000-0000-0000-0000-000000000002",
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      valuation_cutoff:
        "2026-09-15T22:00:00Z",
      calculated_at:
        "2026-09-15T22:00:00Z",
      engine_version: "0.1.0.dev0",
      current_data_as_of:
        "2026-09-15T21:55:00Z",
      historical_data_as_of:
        "2026-09-15T21:55:00Z",
      analytics_as_of_date: "2026-09-15",
    },
    is_complete: true,
    modules: [
      {
        module: "SUMMARY",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "PERFORMANCE",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "ALLOCATION",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "HOLDINGS",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
      {
        module: "MOVERS",
        status: "AVAILABLE",
        error_code: null,
        detail: null,
      },
    ],
    performance: {
      summary: {
        starting_value: "1000.00",
        ending_value: "1100.00",
        value_change: "100.00",
        net_external_flow: "0.00",
        investment_gain_loss: "100.00",
        cumulative_return: 0.1,
        benchmark_cumulative_return: null,
      },
      points: [
        {
          observation_date: "2026-09-01",
          portfolio_value: "1000.00",
          net_external_flow: "0.00",
          daily_return: null,
          cumulative_return: 0,
          data_quality: "CURRENT",
          warnings: [],
        },
        {
          observation_date: "2026-09-15",
          portfolio_value: "1100.00",
          net_external_flow: "0.00",
          daily_return: 0.1,
          cumulative_return: 0.1,
          data_quality: "CURRENT",
          warnings: [],
        },
      ],
      benchmark_points: [],
      portfolio_data_quality: "CURRENT",
      benchmark_data_quality: null,
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        effective_start: "2026-09-01",
        effective_end_exclusive:
          "2026-09-16",
        data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        engine_version: "0.1.0.dev0",
        price_field: "adjusted_close",
        benchmark_asset_id: null,
        benchmark_symbol: null,
      },
    },
    summary: {
      metrics: {
        total_market_value: "1100.00",
        total_market_value_unavailable_reason:
          null,
        net_contributions: "1000.00",
        cost_basis: "900.00",
        cash_balance: "100.00",
        cash_percentage: "0.0909090909",
        cash_percentage_unavailable_reason:
          null,
        unrealized_gain_loss: "100.00",
        unrealized_gain_loss_unavailable_reason:
          null,
        selected_period_realized_gain_loss:
          "25.00",
        selected_period_realized_gain_loss_unavailable_reason:
          null,
        selected_period_income_received:
          "10.00",
        selected_period_income_unavailable_reason:
          null,
      },
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        ledger_as_of:
          "2026-09-15T22:00:00Z",
        current_price_data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        current_price_field: "close",
        accounting_method:
          "WEIGHTED_AVERAGE_BOOK_COST_V1",
        accounting_assumptions: [],
        selected_period_transaction_timezone:
          "UTC",
        net_contributions_scope:
          "LIFETIME_THROUGH_LEDGER_AS_OF",
        selected_period_accounting_scope:
          "REQUESTED_RANGE_INTERSECTED_WITH_LEDGER_AS_OF",
      },
    },
    allocation: {
      allocation_available: true,
      groups: [
        {
          key: "STOCK",
          label: "Stocks",
          is_cash: false,
          asset_count: 1,
          market_value: "1000.00",
          weight: 0.9090909091,
        },
        {
          key: "CASH",
          label: "Cash",
          is_cash: true,
          asset_count: 0,
          market_value: "100.00",
          weight: 0.0909090909,
        },
      ],
      totals: {
        total_market_value: "1100.00",
        invested_value: "1000.00",
        cash_value: "100.00",
        invested_weight: 0.9090909091,
        cash_weight: 0.0909090909,
      },
      data_quality: "CURRENT",
      unavailable_reason: null,
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        as_of:
          "2026-09-15T22:00:00Z",
        data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        price_field: "close",
        grouping_dimension: "ASSET_CLASS",
        supported_grouping_dimensions: [
          "ASSET_CLASS",
        ],
        grouping_source: "Asset.asset_type",
        ordering_rule:
          "SECURITY_WEIGHT_DESC_THEN_GROUP_KEY_CASH_LAST_V1",
        other_grouping_applied: false,
        other_grouping_threshold: null,
        other_grouping_rule:
          "No Other aggregation is applied in the MVP.",
        weight_sum_tolerance: 1e-8,
      },
    },
    holdings: {
      holdings: [],
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        effective_start: "2026-09-01",
        effective_end_exclusive:
          "2026-09-16",
        current_price_as_of:
          "2026-09-15T21:55:00Z",
        period_data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        current_price_field: "close",
        period_price_field:
          "adjusted_close",
      },
    },
    movers: {
      top_gainers: [],
      top_losers: [],
      largest_contributors: [],
      largest_detractors: [],
      reconciliation: {
        status: "AVAILABLE",
        periods: 1,
        cumulative_return: 0.1,
        asset_contribution_total: 0.1,
        unattributed_contribution: 0,
        reconciliation_error: 0,
        unavailable_reason: null,
      },
      data_quality: "CURRENT",
      warnings: [],
      provenance: {
        portfolio_id:
          "00000000-0000-0000-0000-000000000002",
        base_currency: "USD",
        provider: "mock",
        requested_start: "2026-09-01",
        requested_end_exclusive:
          "2026-09-16",
        effective_start: "2026-09-01",
        effective_end_exclusive:
          "2026-09-16",
        current_price_as_of:
          "2026-09-15T21:55:00Z",
        period_data_as_of:
          "2026-09-15T21:55:00Z",
        calculated_at:
          "2026-09-15T22:00:00Z",
        current_price_field: "close",
        period_price_field:
          "adjusted_close",
        attribution_method:
          "ASSET_PNL_WEALTH_LINKED_V1",
        engine_version: "0.1.0.dev0",
      },
    },
    analytics: null,
    review_items: null,
  };
}

describe("DashboardOverview", () => {
  it("renders performance, summary, allocation, holdings, movers, and review items", async () => {
    render(
      <DashboardOverview
        snapshot={snapshotFixture()}
        isLoading={false}
        isFetching={false}
        error={null}
        onRetry={() => undefined}
      />,
    );

    expect(
      screen.getByText("Portfolio performance"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Portfolio summary"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByText("$1,100.00").length,
    ).toBeGreaterThan(0);

    expect(
      await screen.findByTestId(
        "performance-chart",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "allocation-panel",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "holdings-panel",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "movers-panel",
      ),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "review-items-panel",
      ),
    ).toBeInTheDocument();
  });

  it("keeps stale data visible and explicitly labeled", async () => {
    const snapshot = snapshotFixture();

    snapshot.performance!.portfolio_data_quality =
      "STALE";

    render(
      <DashboardOverview
        snapshot={snapshot}
        isLoading={false}
        isFetching={false}
        error={null}
        onRetry={() => undefined}
      />,
    );

    expect(
      screen.getByText("Stale data"),
    ).toBeInTheDocument();

    expect(
      await screen.findByTestId(
        "performance-chart",
      ),
    ).toBeInTheDocument();
  });

  it("shows module-local failure without collapsing the summary", () => {
    const snapshot = snapshotFixture();

    snapshot.performance = null;

    snapshot.modules =
      snapshot.modules.map((module) =>
        module.module === "PERFORMANCE"
          ? {
              ...module,
              status: "UNAVAILABLE",
              error_code:
                "PERFORMANCE_UNAVAILABLE",
              detail:
                "Performance history is incomplete.",
            }
          : module,
      );

    render(
      <DashboardOverview
        snapshot={snapshot}
        isLoading={false}
        isFetching={false}
        error={null}
        onRetry={() => undefined}
      />,
    );

    expect(
      screen.getByText(
        "Performance unavailable",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Performance history is incomplete.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Portfolio summary"),
    ).toBeInTheDocument();
  });
});
````

---

# File: `src/features/dashboard/DashboardOverview.tsx`

````tsx
import { lazy, Suspense } from "react";

import { ApiError } from "../../api/client";
import { LazySection } from "../../components/ui/LazySection";
import { Skeleton } from "../../components/ui/Skeleton";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardSnapshotModule,
  DashboardSnapshotResult,
} from "../../types/dashboard";
import { PerformanceHero } from "./PerformanceHero";
import { PortfolioSummaryCard } from "./PortfolioSummaryCard";

const AllocationPanel = lazy(async () => {
  const module = await import("./AllocationPanel");
  return { default: module.AllocationPanel };
});

const HoldingsPanel = lazy(async () => {
  const module = await import("./HoldingsPanel");
  return { default: module.HoldingsPanel };
});

const MoversPanel = lazy(async () => {
  const module = await import("./MoversPanel");
  return { default: module.MoversPanel };
});

const ReviewItemsPanel = lazy(async () => {
  const module = await import("./ReviewItemsPanel");
  return { default: module.ReviewItemsPanel };
});

interface DashboardOverviewProps {
  snapshot: DashboardSnapshotResult | undefined;
  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  onRetry: () => void;
}

function moduleError(
  snapshot: DashboardSnapshotResult,
  module: DashboardSnapshotModule,
): string | null {
  const state = snapshot.modules.find((candidate) => candidate.module === module);

  if (!state || state.status === "AVAILABLE") {
    return null;
  }

  return state.detail ?? state.error_code ?? `${module} is unavailable.`;
}

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 lg:col-span-8">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="mt-4 h-10 w-56" />
        <Skeleton className="mt-7 h-72 w-full" />
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 lg:col-span-4">
        <Skeleton className="h-5 w-40" />

        <div className="mt-6 space-y-4">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      </section>
    </div>
  );
}

function AllocationSkeleton() {
  return (
    <section
      className="min-h-[24rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading allocation"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-28" />
          <Skeleton className="mt-3 h-6 w-36" />
        </div>

        <Skeleton className="h-8 w-24" />
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }, (_, index) => (
          <Skeleton key={index} className="h-24 w-full" />
        ))}
      </div>

      <Skeleton className="mt-6 h-40 w-full" />
    </section>
  );
}

function HoldingsSkeleton() {
  return (
    <section
      className="min-h-[28rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading holdings"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-28" />
          <Skeleton className="mt-3 h-6 w-32" />
        </div>

        <Skeleton className="h-8 w-36" />
      </div>

      <div className="mt-8 space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <Skeleton key={index} className="h-20 w-full" />
        ))}
      </div>
    </section>
  );
}

function MoversSkeleton() {
  return (
    <section
      className="min-h-[26rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading movers"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-32" />
          <Skeleton className="mt-3 h-6 w-28" />
        </div>

        <Skeleton className="h-8 w-24" />
      </div>

      <Skeleton className="mt-6 h-11 w-full" />

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-40 w-full" />
        ))}
      </div>
    </section>
  );
}

function ReviewItemsSkeleton() {
  return (
    <section
      className="min-h-[24rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
      aria-label="Loading data-quality review items"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <Skeleton className="h-3 w-28" />
          <Skeleton className="mt-3 h-6 w-44" />
        </div>

        <Skeleton className="h-8 w-28" />
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-9 w-24" />
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {Array.from({ length: 3 }, (_, index) => (
          <Skeleton key={index} className="h-32 w-full" />
        ))}
      </div>
    </section>
  );
}

export function DashboardOverview({
  snapshot,
  isLoading,
  isFetching,
  error,
  onRetry,
}: DashboardOverviewProps) {
  if (isLoading && snapshot === undefined) {
    return <DashboardSkeleton />;
  }

  if (error !== null && snapshot === undefined) {
    const apiError = error instanceof ApiError ? error : null;
    const title =
      apiError?.status === 403
        ? "Portfolio access denied"
        : apiError?.status === 404
          ? "Portfolio not found"
          : "Dashboard could not load";

    return (
      <StatePanel
        title={title}
        message={error.message}
        tone="error"
        action={
          <button
            type="button"
            onClick={onRetry}
            className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Retry
          </button>
        }
      />
    );
  }

  if (snapshot === undefined) {
    return (
      <StatePanel
        title="No dashboard snapshot"
        message="No portfolio dashboard data is available for this request."
      />
    );
  }

  const performanceError = moduleError(snapshot, "PERFORMANCE");
  const summaryError = moduleError(snapshot, "SUMMARY");
  const allocationError = moduleError(snapshot, "ALLOCATION");
  const holdingsError = moduleError(snapshot, "HOLDINGS");
  const moversError = moduleError(snapshot, "MOVERS");
  const reviewItemsError = moduleError(snapshot, "REVIEW_ITEMS");

  const hasUsableDashboard =
    snapshot.performance !== null ||
    snapshot.summary !== null ||
    snapshot.allocation !== null ||
    snapshot.holdings !== null ||
    snapshot.movers !== null ||
    snapshot.review_items !== null;

  if (!hasUsableDashboard) {
    return (
      <StatePanel
        title="Portfolio data is not available yet"
        message="The dashboard snapshot loaded, but the performance, summary, allocation, holdings, movers, and review-items modules are unavailable for the selected period."
      />
    );
  }

  return (
    <div className="relative">
      {error !== null ? (
        <div
          className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          Refresh failed. Showing the most recent successful dashboard snapshot.
        </div>
      ) : null}

      {isFetching ? (
        <div
          className="pointer-events-none absolute -top-10 right-0 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800"
          role="status"
          aria-live="polite"
        >
          Refreshing snapshot…
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-8">
          <PerformanceHero
            performance={snapshot.performance}
            currency={snapshot.snapshot.base_currency}
            moduleError={performanceError}
          />
        </div>

        <div className="lg:col-span-4">
          <PortfolioSummaryCard
            summary={snapshot.summary}
            currency={snapshot.snapshot.base_currency}
            moduleError={summaryError}
          />
        </div>
      </div>

      <div className="mt-5">
        <Suspense fallback={<AllocationSkeleton />}>
          <AllocationPanel
            allocation={snapshot.allocation}
            currency={snapshot.snapshot.base_currency}
            moduleError={allocationError}
          />
        </Suspense>
      </div>

      <div className="mt-5">
        <LazySection fallback={<HoldingsSkeleton />}>
          <Suspense fallback={<HoldingsSkeleton />}>
            <HoldingsPanel
              holdings={snapshot.holdings}
              currency={snapshot.snapshot.base_currency}
              portfolioId={snapshot.snapshot.portfolio_id}
              moduleError={holdingsError}
            />
          </Suspense>
        </LazySection>
      </div>

      <div className="mt-5">
        <LazySection fallback={<MoversSkeleton />}>
          <Suspense fallback={<MoversSkeleton />}>
            <MoversPanel
              movers={snapshot.movers}
              portfolioId={snapshot.snapshot.portfolio_id}
              moduleError={moversError}
            />
          </Suspense>
        </LazySection>
      </div>

      <div className="mt-5">
        <LazySection fallback={<ReviewItemsSkeleton />}>
          <Suspense fallback={<ReviewItemsSkeleton />}>
            <ReviewItemsPanel
              key={snapshot.snapshot.snapshot_id}
              reviewItems={snapshot.review_items}
              isSnapshotComplete={snapshot.is_complete}
              moduleError={reviewItemsError}
            />
          </Suspense>
        </LazySection>
      </div>
    </div>
  );
}
````

---

# File: `src/features/dashboard/dateRange.test.ts`

````typescript
import { resolveDashboardDateRange } from "./dateRange";

describe("resolveDashboardDateRange", () => {
  const now = new Date(2026, 8, 15, 12, 0, 0);

  it("uses an exclusive next-day end date", () => {
    expect(resolveDashboardDateRange("1W", "2025-01-01T00:00:00Z", now)).toEqual({
      start: "2026-09-08",
      end: "2026-09-16",
    });
  });

  it("uses portfolio creation date for the All range", () => {
    expect(resolveDashboardDateRange("ALL", "2025-01-02T15:00:00Z", now)).toEqual({
      start: "2025-01-02",
      end: "2026-09-16",
    });
  });
});
````

---

# File: `src/features/dashboard/dateRange.ts`

````typescript
export type DashboardRange = "1W" | "1M" | "3M" | "6M" | "YTD" | "1Y" | "ALL";

export const DASHBOARD_RANGES: readonly DashboardRange[] = [
  "1W",
  "1M",
  "3M",
  "6M",
  "YTD",
  "1Y",
  "ALL",
];

function startOfLocalDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function addDays(value: Date, days: number): Date {
  const result = new Date(value);
  result.setDate(result.getDate() + days);
  return result;
}

function addMonths(value: Date, months: number): Date {
  const result = new Date(value);
  result.setMonth(result.getMonth() + months);
  return result;
}

function addYears(value: Date, years: number): Date {
  const result = new Date(value);
  result.setFullYear(result.getFullYear() + years);
  return result;
}

export function formatLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function resolveDashboardDateRange(
  range: DashboardRange,
  portfolioCreatedAt: string,
  now: Date = new Date(),
): { start: string; end: string } {
  const today = startOfLocalDay(now);
  const endExclusive = addDays(today, 1);
  let start: Date;

  switch (range) {
    case "1W":
      start = addDays(today, -7);
      break;
    case "1M":
      start = addMonths(today, -1);
      break;
    case "3M":
      start = addMonths(today, -3);
      break;
    case "6M":
      start = addMonths(today, -6);
      break;
    case "YTD":
      start = new Date(today.getFullYear(), 0, 1);
      break;
    case "1Y":
      start = addYears(today, -1);
      break;
    case "ALL": {
      const [createdDate] = portfolioCreatedAt.split("T");
      return {
        start: createdDate || formatLocalIsoDate(addYears(today, -1)),
        end: formatLocalIsoDate(endExclusive),
      };
    }
  }

  return {
    start: formatLocalIsoDate(start),
    end: formatLocalIsoDate(endExclusive),
  };
}
````

---

# File: `src/features/dashboard/formatting.ts`

````typescript
export function formatCurrency(
  value: string | null,
  currency: string,
): string {
  if (value === null) {
    return "Not available";
  }

  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numericValue);
}

export function formatPercent(
  value: number | null,
  fractionDigits = 2,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    signDisplay: "exceptZero",
  }).format(value);
}

export function formatDecimalPercent(value: string | null): string {
  if (value === null) {
    return "Not available";
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue)
    ? formatPercent(numericValue, 1)
    : "Not available";
}

export function formatDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function formatDateTime(value: string | null): string {
  if (value === null) {
    return "Not available";
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(value));
}

export function humanizeCode(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const words = value.toLowerCase().replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
````

---

# File: `src/features/dashboard/HoldingsPanel.test.tsx`

````tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { HoldingsPanel } from "./HoldingsPanel";
import type {
  DashboardHolding,
  DashboardHoldingsResult,
} from "../../types/dashboard";

vi.mock("../../components/charts/HoldingSparkline", () => ({
  HoldingSparkline: ({ symbol }: { symbol: string }) => (
    <div data-testid={`sparkline-${symbol}`}>Sparkline</div>
  ),
}));

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function holding(
  assetId: string,
  symbol: string,
  marketValue: string,
  weight: number,
  selectedReturn: number,
): DashboardHolding {
  return {
    asset_id: assetId,
    symbol,
    name: `${symbol} Incorporated`,
    asset_type: "STOCK",
    currency: "USD",
    quantity: "10.00000000",
    current_price: "100.00",
    current_price_date: "2026-09-15",
    current_price_retrieved_at: "2026-09-15T21:55:00Z",
    stale_trading_sessions: 0,
    market_value: marketValue,
    weight,
    weight_unavailable_reason: null,
    selected_period_return: selectedReturn,
    selected_period_return_unavailable_reason: null,
    contribution_to_return: null,
    contribution_unavailable_reason: "CONTRIBUTION_NOT_CALCULATED",
    sparkline: [
      {
        observation_date: "2026-09-01",
        adjusted_close: "90.00",
      },
      {
        observation_date: "2026-09-02",
        adjusted_close: null,
      },
      {
        observation_date: "2026-09-15",
        adjusted_close: "100.00",
      },
    ],
    data_quality: "CURRENT",
    warnings: [],
  };
}

function holdingsFixture(): DashboardHoldingsResult {
  return {
    holdings: [
      holding(
        "00000000-0000-0000-0000-000000000011",
        "AAA",
        "100.00",
        0.1,
        0.05,
      ),
      holding(
        "00000000-0000-0000-0000-000000000012",
        "BBB",
        "900.00",
        0.9,
        -0.02,
      ),
    ],
    data_quality: "CURRENT",
    warnings: [],
    provenance: {
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      current_price_as_of: "2026-09-15T21:55:00Z",
      period_data_as_of: "2026-09-15T21:55:00Z",
      calculated_at: "2026-09-15T22:00:00Z",
      current_price_field: "close",
      period_price_field: "adjusted_close",
    },
  };
}

function renderPanel() {
  return render(
    <MemoryRouter
      initialEntries={[
        `/portfolios/${PORTFOLIO_ID}/dashboard?range=3M`,
      ]}
    >
      <HoldingsPanel
        holdings={holdingsFixture()}
        currency="USD"
        portfolioId={PORTFOLIO_ID}
        moduleError={null}
      />
    </MemoryRouter>,
  );
}

function holdingLinks(): HTMLAnchorElement[] {
  return screen.getAllByRole("link", {
    name: /Open .* holding details/,
  }) as HTMLAnchorElement[];
}

describe("HoldingsPanel", () => {
  it("sorts deterministically by market value and preserves route context", () => {
    renderPanel();

    const links = holdingLinks();

    expect(links[0]).toHaveAccessibleName("Open BBB holding details");
    expect(links[1]).toHaveAccessibleName("Open AAA holding details");
    expect(links[0]?.getAttribute("href")).toBe(
      `/portfolios/${PORTFOLIO_ID}/holdings/00000000-0000-0000-0000-000000000012?range=3M`,
    );
    expect(screen.getByTestId("sparkline-BBB")).toBeInTheDocument();
  });

  it("supports keyboard-accessible native links and deterministic symbol sorting", () => {
    renderPanel();

    fireEvent.change(screen.getByRole("combobox", { name: "Sort holdings by" }), {
      target: { value: "SYMBOL" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Sort holdings ascending" }),
    );

    const links = holdingLinks();

    expect(links[0]).toHaveAccessibleName("Open AAA holding details");
    links[0]?.focus();
    expect(links[0]).toHaveFocus();
  });

  it("uses text and directional symbols in addition to semantic colors", () => {
    renderPanel();

    expect(screen.getByText("▲ +5.00%")).toBeInTheDocument();
    expect(screen.getByText("▼ -2.00%")).toBeInTheDocument();
  });
});
````

---

# File: `src/features/dashboard/HoldingsPanel.tsx`

````tsx
import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router";

import { HoldingSparkline } from "../../components/charts/HoldingSparkline";
import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardHolding,
  DashboardHoldingsResult,
} from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
  humanizeCode,
} from "./formatting";

const HOLDINGS_PAGE_SIZE = 25;

type HoldingsSortKey =
  | "MARKET_VALUE"
  | "WEIGHT"
  | "RETURN"
  | "SYMBOL";
type HoldingsSortDirection = "ASC" | "DESC";

interface HoldingsPanelProps {
  holdings: DashboardHoldingsResult | null;
  currency: string;
  portfolioId: string;
  moduleError: string | null;
}

function compareText(left: string, right: string): number {
  if (left === right) {
    return 0;
  }

  return left < right ? -1 : 1;
}

function normalizedDecimalParts(value: string): {
  sign: number;
  integer: string;
  fraction: string;
} {
  const trimmed = value.trim();
  const sign = trimmed.startsWith("-") ? -1 : 1;
  const unsigned = trimmed.replace(/^[+-]/, "");
  const [rawInteger = "0", rawFraction = ""] = unsigned.split(".", 2);
  const integer = rawInteger.replace(/^0+(?=\d)/, "") || "0";
  const fraction = rawFraction.replace(/0+$/, "");

  return { sign, integer, fraction };
}

function compareDecimalStrings(left: string, right: string): number {
  const a = normalizedDecimalParts(left);
  const b = normalizedDecimalParts(right);

  if (a.sign !== b.sign) {
    return a.sign < b.sign ? -1 : 1;
  }

  const magnitudeSign = a.sign;

  if (a.integer.length !== b.integer.length) {
    return a.integer.length < b.integer.length
      ? -1 * magnitudeSign
      : 1 * magnitudeSign;
  }

  const integerComparison = compareText(a.integer, b.integer);
  if (integerComparison !== 0) {
    return integerComparison * magnitudeSign;
  }

  const fractionLength = Math.max(a.fraction.length, b.fraction.length);
  const fractionComparison = compareText(
    a.fraction.padEnd(fractionLength, "0"),
    b.fraction.padEnd(fractionLength, "0"),
  );

  return fractionComparison * magnitudeSign;
}

function nullableComparison<T>(
  left: T | null,
  right: T | null,
  compare: (a: T, b: T) => number,
): number {
  if (left === null && right === null) {
    return 0;
  }

  if (left === null) {
    return 1;
  }

  if (right === null) {
    return -1;
  }

  return compare(left, right);
}

function compareHoldingMetric(
  left: DashboardHolding,
  right: DashboardHolding,
  sortKey: HoldingsSortKey,
): number {
  if (sortKey === "SYMBOL") {
    return compareText(left.symbol.toUpperCase(), right.symbol.toUpperCase());
  }

  if (sortKey === "MARKET_VALUE") {
    return nullableComparison(
      left.market_value,
      right.market_value,
      compareDecimalStrings,
    );
  }

  const leftValue =
    sortKey === "WEIGHT" ? left.weight : left.selected_period_return;
  const rightValue =
    sortKey === "WEIGHT" ? right.weight : right.selected_period_return;

  return nullableComparison(leftValue, rightValue, (a, b) => a - b);
}

function metricIsUnavailable(
  holding: DashboardHolding,
  sortKey: HoldingsSortKey,
): boolean {
  if (sortKey === "SYMBOL") {
    return false;
  }

  if (sortKey === "MARKET_VALUE") {
    return holding.market_value === null;
  }

  return sortKey === "WEIGHT"
    ? holding.weight === null
    : holding.selected_period_return === null;
}

function sortedHoldings(
  holdings: DashboardHolding[],
  sortKey: HoldingsSortKey,
  direction: HoldingsSortDirection,
): DashboardHolding[] {
  return [...holdings].sort((left, right) => {
    const leftUnavailable = metricIsUnavailable(left, sortKey);
    const rightUnavailable = metricIsUnavailable(right, sortKey);

    if (leftUnavailable !== rightUnavailable) {
      return leftUnavailable ? 1 : -1;
    }

    const metricComparison = compareHoldingMetric(left, right, sortKey);

    if (metricComparison !== 0) {
      return direction === "ASC" ? metricComparison : -metricComparison;
    }

    const symbolComparison = compareText(
      left.symbol.toUpperCase(),
      right.symbol.toUpperCase(),
    );

    if (symbolComparison !== 0) {
      return symbolComparison;
    }

    return compareText(left.asset_id, right.asset_id);
  });
}

function initials(symbol: string): string {
  return symbol.slice(0, 2).toUpperCase();
}

function movementPresentation(value: number | null): {
  label: string;
  className: string;
} {
  if (value === null) {
    return {
      label: "Not available",
      className: "text-slate-500",
    };
  }

  if (value > 0) {
    return {
      label: `▲ ${formatPercent(value)}`,
      className: "text-emerald-700",
    };
  }

  if (value < 0) {
    return {
      label: `▼ ${formatPercent(value)}`,
      className: "text-rose-700",
    };
  }

  return {
    label: `• ${formatPercent(value)}`,
    className: "text-slate-700",
  };
}

function HoldingRow({
  holding,
  currency,
  portfolioId,
}: {
  holding: DashboardHolding;
  currency: string;
  portfolioId: string;
}) {
  const location = useLocation();
  const movement = movementPresentation(holding.selected_period_return);
  const detailPath = `/portfolios/${encodeURIComponent(
    portfolioId,
  )}/holdings/${encodeURIComponent(holding.asset_id)}${location.search}`;
  const returnReason = humanizeCode(
    holding.selected_period_return_unavailable_reason,
  );
  const weightReason = humanizeCode(holding.weight_unavailable_reason);

  return (
    <li>
      <Link
        to={detailPath}
        state={{
          holding: {
            assetId: holding.asset_id,
            symbol: holding.symbol,
            name: holding.name,
            assetType: holding.asset_type,
            currency: holding.currency,
          },
        }}
        className="group grid gap-3 rounded-2xl border border-transparent px-3 py-4 outline-none transition hover:border-blue-100 hover:bg-blue-50/40 focus-visible:border-blue-300 focus-visible:ring-2 focus-visible:ring-blue-500 md:grid-cols-[minmax(12rem,1.4fr)_minmax(7rem,0.8fr)_minmax(7rem,0.8fr)_minmax(6rem,0.65fr)_minmax(7rem,0.7fr)_minmax(8rem,0.9fr)] md:items-center"
        aria-label={`Open ${holding.symbol} holding details`}
      >
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-700"
            aria-hidden="true"
          >
            {initials(holding.symbol)}
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-950 group-hover:text-blue-700">
                {holding.symbol}
              </span>
              <DataQualityBadge quality={holding.data_quality} />
            </div>
            <p className="truncate text-sm text-slate-600">{holding.name}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {holding.asset_type} · {holding.currency}
            </p>
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">Price</p>
          <p
            className="font-medium tabular-nums text-slate-950"
            title={
              holding.current_price === null
                ? undefined
                : `Exact price: ${holding.current_price} ${holding.currency}`
            }
          >
            {formatCurrency(holding.current_price, holding.currency)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {formatDateTime(holding.current_price_retrieved_at)}
          </p>
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">Value</p>
          <p
            className="font-medium tabular-nums text-slate-950"
            title={
              holding.market_value === null
                ? undefined
                : `Exact market value: ${holding.market_value} ${currency}`
            }
          >
            {formatCurrency(holding.market_value, currency)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            Qty {holding.quantity}
          </p>
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">Weight</p>
          <p
            className="font-medium tabular-nums text-slate-950"
            title={
              holding.weight === null
                ? undefined
                : `Exact weight: ${holding.weight}`
            }
          >
            {formatPercent(holding.weight)}
          </p>
          {holding.weight === null && weightReason ? (
            <p className="mt-0.5 text-xs text-slate-500">{weightReason}</p>
          ) : null}
        </div>

        <div>
          <p className="text-xs font-medium text-slate-500 md:hidden">
            Selected-period return
          </p>
          <p className={`font-semibold tabular-nums ${movement.className}`}>
            {movement.label}
          </p>
          {holding.selected_period_return === null && returnReason ? (
            <p className="mt-0.5 text-xs text-slate-500">{returnReason}</p>
          ) : null}
        </div>

        <div>
          <p className="mb-1 text-xs font-medium text-slate-500 md:hidden">
            Price trend
          </p>
          <HoldingSparkline
            points={holding.sparkline}
            symbol={holding.symbol}
            currency={holding.currency}
          />
        </div>
      </Link>
    </li>
  );
}

export function HoldingsPanel({
  holdings,
  currency,
  portfolioId,
  moduleError,
}: HoldingsPanelProps) {
  const [sortKey, setSortKey] = useState<HoldingsSortKey>("MARKET_VALUE");
  const [direction, setDirection] = useState<HoldingsSortDirection>("DESC");
  const [page, setPage] = useState(0);

  const ordered = useMemo(
    () =>
      holdings === null
        ? []
        : sortedHoldings(holdings.holdings, sortKey, direction),
    [direction, holdings, sortKey],
  );
  const pageCount = Math.max(1, Math.ceil(ordered.length / HOLDINGS_PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const visibleHoldings = ordered.slice(
    safePage * HOLDINGS_PAGE_SIZE,
    (safePage + 1) * HOLDINGS_PAGE_SIZE,
  );

  return (
    <DashboardCard
      title="Holdings"
      eyebrow="Portfolio drivers"
      actions={
        holdings ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <DataQualityBadge quality={holdings.data_quality} />
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <span>Sort</span>
              <select
                value={sortKey}
                onChange={(event) => {
                  setSortKey(event.target.value as HoldingsSortKey);
                  setPage(0);
                }}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-800 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                aria-label="Sort holdings by"
              >
                <option value="MARKET_VALUE">Market value</option>
                <option value="WEIGHT">Weight</option>
                <option value="RETURN">Selected return</option>
                <option value="SYMBOL">Symbol</option>
              </select>
            </label>
            <button
              type="button"
              onClick={() => {
                setDirection((current) => (current === "ASC" ? "DESC" : "ASC"));
                setPage(0);
              }}
              className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500"
              aria-label={
                direction === "ASC"
                  ? "Sort holdings descending"
                  : "Sort holdings ascending"
              }
            >
              {direction === "ASC" ? "↑ Asc" : "↓ Desc"}
            </button>
          </div>
        ) : undefined
      }
    >
      {holdings === null ? (
        <StatePanel
          title="Holdings unavailable"
          message={
            moduleError ??
            "The dashboard snapshot did not return a usable holdings result."
          }
          tone="error"
        />
      ) : holdings.holdings.length === 0 ? (
        <StatePanel
          title="No current holdings"
          message="This portfolio has no open security positions at the snapshot cutoff."
        />
      ) : (
        <div>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3 text-xs text-slate-500">
            <p>
              {holdings.holdings.length} holding
              {holdings.holdings.length === 1 ? "" : "s"} · Current prices as of {" "}
              {formatDateTime(holdings.provenance.current_price_as_of)}
            </p>
            <p>
              Historical prices: {holdings.provenance.period_price_field} · {" "}
              {formatDateTime(holdings.provenance.period_data_as_of)}
            </p>
          </div>

          <div
            className="hidden grid-cols-[minmax(12rem,1.4fr)_minmax(7rem,0.8fr)_minmax(7rem,0.8fr)_minmax(6rem,0.65fr)_minmax(7rem,0.7fr)_minmax(8rem,0.9fr)] gap-3 border-b border-slate-200 px-3 pb-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500 md:grid"
            aria-hidden="true"
          >
            <span>Security</span>
            <span>Price</span>
            <span>Value</span>
            <span>Weight</span>
            <span>Return</span>
            <span>Trend</span>
          </div>

          <ul className="divide-y divide-slate-100" aria-label="Portfolio holdings">
            {visibleHoldings.map((holding) => (
              <HoldingRow
                key={holding.asset_id}
                holding={holding}
                currency={currency}
                portfolioId={portfolioId}
              />
            ))}
          </ul>

          {pageCount > 1 ? (
            <nav
              className="mt-5 flex items-center justify-between gap-3 border-t border-slate-100 pt-4"
              aria-label="Holdings pages"
            >
              <p className="text-xs text-slate-500" aria-live="polite">
                Page {safePage + 1} of {pageCount}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={safePage === 0}
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none disabled:cursor-not-allowed disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={safePage >= pageCount - 1}
                  onClick={() =>
                    setPage((current) => Math.min(pageCount - 1, current + 1))
                  }
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none disabled:cursor-not-allowed disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-blue-500"
                >
                  Next
                </button>
              </div>
            </nav>
          ) : null}

          {holdings.warnings.length > 0 ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <p className="font-semibold">Holdings data-quality note</p>
              <p className="mt-1 leading-6">
                {holdings.warnings[0]?.message}
                {holdings.warnings.length > 1
                  ? ` (+${holdings.warnings.length - 1} more)`
                  : ""}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </DashboardCard>
  );
}
````

---

# File: `src/features/dashboard/MoversPanel.test.tsx`

````tsx
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { MoversPanel } from "./MoversPanel";
import type {
  DashboardMover,
  DashboardMoversResult,
} from "../../types/dashboard";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function mover(
  assetId: string,
  symbol: string,
  selectedPeriodReturn: number,
  contribution: number,
  isCurrentHolding = true,
): DashboardMover {
  return {
    asset_id: assetId,
    symbol,
    name: `${symbol} Incorporated`,
    asset_type: "STOCK",
    currency: "USD",
    is_current_holding: isCurrentHolding,
    quantity: isCurrentHolding ? "10.000000000000" : null,
    current_price: isCurrentHolding ? "100.00000000" : null,
    current_price_date: isCurrentHolding ? "2026-09-15" : null,
    current_price_retrieved_at: isCurrentHolding
      ? "2026-09-15T21:55:00Z"
      : null,
    stale_trading_sessions: isCurrentHolding ? 0 : null,
    market_value: isCurrentHolding ? "1000.00000000" : null,
    weight: isCurrentHolding ? 0.5 : null,
    selected_period_return: selectedPeriodReturn,
    contribution_to_return: contribution,
    sparkline: [],
    data_quality: "CURRENT",
    unavailable_reasons: isCurrentHolding ? [] : ["NOT_CURRENT_HOLDING"],
  };
}

function moversFixture(): DashboardMoversResult {
  const aaa = mover(
    "00000000-0000-0000-0000-000000000011",
    "AAA",
    0.15,
    0.06,
  );
  const bbb = mover(
    "00000000-0000-0000-0000-000000000012",
    "BBB",
    0.12,
    0.04,
  );
  const ccc = mover(
    "00000000-0000-0000-0000-000000000013",
    "CCC",
    -0.08,
    -0.03,
  );
  const sold = mover(
    "00000000-0000-0000-0000-000000000014",
    "SOLD",
    -0.04,
    0.02,
    false,
  );

  return {
    top_gainers: [aaa, bbb],
    top_losers: [ccc, sold],
    largest_contributors: [aaa, bbb, sold],
    largest_detractors: [ccc],
    reconciliation: {
      status: "AVAILABLE",
      periods: 10,
      cumulative_return: 0.09,
      asset_contribution_total: 0.09,
      unattributed_contribution: 0.001,
      reconciliation_error: 0,
      unavailable_reason: null,
    },
    data_quality: "CURRENT",
    warnings: [],
    provenance: {
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      current_price_as_of: "2026-09-15T21:55:00Z",
      period_data_as_of: "2026-09-15T21:55:00Z",
      calculated_at: "2026-09-15T22:00:00Z",
      current_price_field: "close",
      period_price_field: "adjusted_close",
      attribution_method: "ASSET_PNL_WEALTH_LINKED_V1",
      engine_version: "0.1.0.dev0",
    },
  };
}

function renderMovers(result = moversFixture()) {
  render(
    <MemoryRouter
      initialEntries={[`/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`]}
    >
      <MoversPanel
        movers={result}
        portfolioId={PORTFOLIO_ID}
        moduleError={null}
      />
    </MemoryRouter>,
  );
}

describe("MoversPanel", () => {
  it("renders server-provided ranking order without client re-sorting", () => {
    renderMovers();

    const cards = screen.getAllByTestId("mover-card");
    expect(within(cards[0]!).getByText("AAA")).toBeInTheDocument();
    expect(within(cards[1]!).getByText("BBB")).toBeInTheDocument();
  });

  it("switches ranking tabs with keyboard navigation", () => {
    renderMovers();

    const gainers = screen.getByRole("tab", { name: "Top Gainers" });
    fireEvent.keyDown(gainers, { key: "ArrowRight" });

    const losers = screen.getByRole("tab", { name: "Top Losers" });
    expect(losers).toHaveAttribute("aria-selected", "true");
    expect(losers).toHaveFocus();
    expect(screen.getByText("CCC")).toBeInTheDocument();
  });


  it("preserves contributor order and keeps sold historical positions visible", () => {
    renderMovers();

    fireEvent.click(
      screen.getByRole("tab", { name: "Largest Contributors" }),
    );

    const cards = screen.getAllByTestId("mover-card");
    expect(within(cards[0]!).getByText("AAA")).toBeInTheDocument();
    expect(within(cards[1]!).getByText("BBB")).toBeInTheDocument();
    expect(within(cards[2]!).getByText("SOLD")).toBeInTheDocument();
    expect(
      within(cards[2]!).getByText("Historical position"),
    ).toBeInTheDocument();
  });

  it("preserves portfolio range context in mover detail links", () => {
    renderMovers();

    expect(
      screen.getByRole("link", { name: "Open AAA holding details" }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/holdings/00000000-0000-0000-0000-000000000011?range=6M`,
    );
  });

  it("renders backend reconciliation and unattributed contribution metadata", () => {
    renderMovers();

    expect(screen.getByText("Reconciled")).toBeInTheDocument();
    expect(screen.getByText("Unattributed")).toBeInTheDocument();
    expect(screen.getByText("+0.10%")).toBeInTheDocument();
    expect(screen.getByText("Reconciliation error")).toBeInTheDocument();
  });


  it("shows a module-local unavailable state", () => {
    render(
      <MemoryRouter>
        <MoversPanel
          movers={null}
          portfolioId={PORTFOLIO_ID}
          moduleError="Mover attribution inputs are unavailable."
        />
      </MemoryRouter>,
    );

    expect(screen.getByText("Movers unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("Mover attribution inputs are unavailable."),
    ).toBeInTheDocument();
  });

  it("shows explicit attribution unavailability without fabricating values", () => {
    const result = moversFixture();
    result.reconciliation = {
      status: "UNAVAILABLE",
      periods: 0,
      cumulative_return: null,
      asset_contribution_total: null,
      unattributed_contribution: null,
      reconciliation_error: null,
      unavailable_reason: "PORTFOLIO_TWR_UNAVAILABLE",
    };
    result.data_quality = "PARTIAL";

    renderMovers(result);

    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Portfolio twr unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
  });
});
````

---

# File: `src/features/dashboard/MoversPanel.tsx`

````tsx
import {
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { Link, useLocation } from "react-router";

import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
  DashboardMover,
  DashboardMoversResult,
} from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
  humanizeCode,
} from "./formatting";

type MoversTabKey =
  | "GAINERS"
  | "LOSERS"
  | "CONTRIBUTORS"
  | "DETRACTORS";

interface MoversPanelProps {
  movers: DashboardMoversResult | null;
  portfolioId: string;
  moduleError: string | null;
}

const TABS: ReadonlyArray<{
  key: MoversTabKey;
  label: string;
}> = [
  { key: "GAINERS", label: "Top Gainers" },
  { key: "LOSERS", label: "Top Losers" },
  { key: "CONTRIBUTORS", label: "Largest Contributors" },
  { key: "DETRACTORS", label: "Largest Detractors" },
];

function itemsForTab(
  movers: DashboardMoversResult,
  tab: MoversTabKey,
): DashboardMover[] {
  if (tab === "GAINERS") {
    return movers.top_gainers;
  }

  if (tab === "LOSERS") {
    return movers.top_losers;
  }

  if (tab === "CONTRIBUTORS") {
    return movers.largest_contributors;
  }

  return movers.largest_detractors;
}

function emptyMessage(tab: MoversTabKey): string {
  if (tab === "GAINERS") {
    return "No positive selected-period holding returns are available.";
  }

  if (tab === "LOSERS") {
    return "No negative selected-period holding returns are available.";
  }

  if (tab === "CONTRIBUTORS") {
    return "No positive selected-period return contributions are available.";
  }

  return "No negative selected-period return contributions are available.";
}

function primaryMetric(
  mover: DashboardMover,
  tab: MoversTabKey,
): number | null {
  return tab === "GAINERS" || tab === "LOSERS"
    ? mover.selected_period_return
    : mover.contribution_to_return;
}

function primaryMetricLabel(tab: MoversTabKey): string {
  return tab === "GAINERS" || tab === "LOSERS"
    ? "Selected-period return"
    : "Contribution to return";
}

function metricPresentation(value: number | null): {
  text: string;
  className: string;
} {
  if (value === null || !Number.isFinite(value)) {
    return {
      text: "Not available",
      className: "text-slate-500",
    };
  }

  if (value > 0) {
    return {
      text: `▲ ${formatPercent(value)}`,
      className: "text-emerald-700",
    };
  }

  if (value < 0) {
    return {
      text: `▼ ${formatPercent(value)}`,
      className: "text-rose-700",
    };
  }

  return {
    text: `• ${formatPercent(value)}`,
    className: "text-slate-700",
  };
}

function MoverCard({
  mover,
  tab,
  portfolioId,
}: {
  mover: DashboardMover;
  tab: MoversTabKey;
  portfolioId: string;
}) {
  const location = useLocation();
  const metric = primaryMetric(mover, tab);
  const presentation = metricPresentation(metric);
  const detailPath = `/portfolios/${encodeURIComponent(
    portfolioId,
  )}/holdings/${encodeURIComponent(mover.asset_id)}${location.search}`;

  return (
    <li data-testid="mover-card">
      <Link
        to={detailPath}
        state={{
          holding: {
            assetId: mover.asset_id,
            symbol: mover.symbol,
            name: mover.name,
            assetType: mover.asset_type,
            currency: mover.currency,
          },
        }}
        className="group block rounded-2xl border border-slate-200 bg-white p-4 outline-none transition hover:border-blue-200 hover:bg-blue-50/30 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        aria-label={`Open ${mover.symbol} holding details`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-950 group-hover:text-blue-700">
                {mover.symbol}
              </span>
              <DataQualityBadge quality={mover.data_quality} />
              {!mover.is_current_holding ? (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-600">
                  Historical position
                </span>
              ) : null}
            </div>
            <p className="mt-1 truncate text-sm text-slate-600">
              {mover.name}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {mover.asset_type} · {mover.currency}
            </p>
          </div>

          <div className="shrink-0 text-right">
            <p className="text-xs font-medium text-slate-500">
              {primaryMetricLabel(tab)}
            </p>
            <p
              className={`mt-1 font-semibold tabular-nums ${presentation.className}`}
              data-mover-primary-metric={metric ?? undefined}
            >
              {presentation.text}
            </p>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-slate-500">Period return</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatPercent(mover.selected_period_return)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Contribution</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatPercent(mover.contribution_to_return)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Weight</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatPercent(mover.weight)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Current value</dt>
            <dd className="mt-0.5 font-medium tabular-nums text-slate-900">
              {formatCurrency(mover.market_value, mover.currency)}
            </dd>
          </div>
        </dl>

        {mover.unavailable_reasons.length > 0 ? (
          <p className="mt-3 text-xs text-slate-500">
            {mover.unavailable_reasons
              .map((reason) => humanizeCode(reason))
              .filter((reason): reason is string => reason !== null)
              .join(" · ")}
          </p>
        ) : null}
      </Link>
    </li>
  );
}

function ReconciliationSummary({
  movers,
}: {
  movers: DashboardMoversResult;
}) {
  const reconciliation = movers.reconciliation;
  const unavailableReason = humanizeCode(reconciliation.unavailable_reason);

  return (
    <div
      className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
      aria-label="Return contribution reconciliation"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Attribution reconciliation
          </p>
          <p className="mt-1 text-sm text-slate-700">
            {reconciliation.status === "AVAILABLE"
              ? `${reconciliation.periods} linked return periods`
              : unavailableReason ?? "Contribution attribution is unavailable."}
          </p>
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
            reconciliation.status === "AVAILABLE"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-800"
          }`}
        >
          {reconciliation.status === "AVAILABLE" ? "Reconciled" : "Unavailable"}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm lg:grid-cols-4">
        <div>
          <dt className="text-xs text-slate-500">Portfolio TWR</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-cumulative-return={reconciliation.cumulative_return ?? undefined}
          >
            {formatPercent(reconciliation.cumulative_return)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Asset contributions</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-asset-contribution-total={
              reconciliation.asset_contribution_total ?? undefined
            }
          >
            {formatPercent(reconciliation.asset_contribution_total)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Unattributed</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-unattributed-contribution={
              reconciliation.unattributed_contribution ?? undefined
            }
          >
            {formatPercent(reconciliation.unattributed_contribution)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Reconciliation error</dt>
          <dd
            className="mt-0.5 font-semibold tabular-nums text-slate-950"
            data-reconciliation-error={
              reconciliation.reconciliation_error ?? undefined
            }
          >
            {formatPercent(reconciliation.reconciliation_error)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function MoversPanel({
  movers,
  portfolioId,
  moduleError,
}: MoversPanelProps) {
  const [activeTab, setActiveTab] = useState<MoversTabKey>("GAINERS");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  if (moduleError !== null) {
    return (
      <StatePanel
        title="Movers unavailable"
        message={moduleError}
        tone="error"
      />
    );
  }

  if (movers === null) {
    return (
      <StatePanel
        title="Movers unavailable"
        message="No mover rankings are available for this dashboard snapshot."
      />
    );
  }

  const activeIndex = TABS.findIndex((tab) => tab.key === activeTab);
  const activeItems = itemsForTab(movers, activeTab);

  function activateTab(index: number) {
    const tab = TABS[index];
    if (!tab) {
      return;
    }

    setActiveTab(tab.key);
    tabRefs.current[index]?.focus();
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      activateTab((activeIndex + 1) % TABS.length);
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      activateTab((activeIndex - 1 + TABS.length) % TABS.length);
      return;
    }

    if (event.key === "Home") {
      event.preventDefault();
      activateTab(0);
      return;
    }

    if (event.key === "End") {
      event.preventDefault();
      activateTab(TABS.length - 1);
    }
  }

  return (
    <DashboardCard
      title="Movers"
      eyebrow="Selected-period drivers"
      actions={<DataQualityBadge quality={movers.data_quality} />}
    >
      <p className="text-sm text-slate-600">
        Rankings are supplied in canonical server order with deterministic
        tie-breaking. React does not re-rank returns or contributions.
      </p>

      <div
        className="mt-5 flex gap-1 overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50 p-1"
        role="tablist"
        aria-label="Portfolio mover rankings"
      >
        {TABS.map((tab, index) => {
          const selected = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              ref={(node) => {
                tabRefs.current[index] = node;
              }}
              type="button"
              role="tab"
              id={`movers-tab-${tab.key.toLowerCase()}`}
              aria-controls="movers-tabpanel"
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActiveTab(tab.key)}
              onKeyDown={handleTabKeyDown}
              className={`shrink-0 rounded-xl px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                selected
                  ? "bg-slate-950 text-white"
                  : "text-slate-600 hover:bg-white hover:text-slate-950"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div
        id="movers-tabpanel"
        role="tabpanel"
        aria-labelledby={`movers-tab-${activeTab.toLowerCase()}`}
        className="mt-5"
      >
        {activeItems.length === 0 ? (
          <StatePanel
            title={TABS[activeIndex]?.label ?? "Movers"}
            message={emptyMessage(activeTab)}
          />
        ) : (
          <ol className="grid gap-3 lg:grid-cols-2" aria-label="Server-ranked movers">
            {activeItems.map((mover) => (
              <MoverCard
                key={mover.asset_id}
                mover={mover}
                tab={activeTab}
                portfolioId={portfolioId}
              />
            ))}
          </ol>
        )}
      </div>

      <div className="mt-5">
        <ReconciliationSummary movers={movers} />
      </div>

      {movers.warnings.length > 0 ? (
        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            Movers notes
          </p>
          <ul className="mt-2 space-y-1 text-sm text-amber-950">
            {movers.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
        <p>
          Period: {movers.provenance.effective_start} to {" "}
          {movers.provenance.effective_end_exclusive} · Provider: {" "}
          {movers.provenance.provider}
        </p>
        <p>
          Period data as of {formatDateTime(movers.provenance.period_data_as_of)} · {" "}
          Current prices as of {formatDateTime(movers.provenance.current_price_as_of)}
        </p>
        <p>
          Attribution: {movers.provenance.attribution_method} · Engine {" "}
          {movers.provenance.engine_version}
        </p>
      </div>
    </DashboardCard>
  );
}
````

---

# File: `src/features/dashboard/PerformanceHero.tsx`

````tsx
import {
  lazy,
  Suspense,
  useState,
} from "react";

import type {
  PerformanceChartMode,
} from "../../components/charts/PerformanceChart";
import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import type { DashboardPerformanceResult } from "../../types/dashboard";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
} from "./formatting";

const PerformanceChart = lazy(async () => {
  const module = await import(
    "../../components/charts/PerformanceChart"
  );

  return {
    default: module.PerformanceChart,
  };
});

interface PerformanceHeroProps {
  performance: DashboardPerformanceResult | null;
  currency: string;
  moduleError: string | null;
}

function signedTone(value: number | null): string {
  if (value === null || value === 0) {
    return "text-slate-700";
  }

  return value > 0 ? "text-emerald-700" : "text-rose-700";
}

export function PerformanceHero({
  performance,
  currency,
  moduleError,
}: PerformanceHeroProps) {
  const [mode, setMode] = useState<PerformanceChartMode>("VALUE");

  return (
    <DashboardCard
      title="Portfolio performance"
      eyebrow="Overview"
      className="min-h-136"
      actions={
        performance ? (
          <div className="flex items-center gap-2">
            <DataQualityBadge quality={performance.portfolio_data_quality} />
            <div
              className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1"
              aria-label="Performance chart view"
            >
              {(["VALUE", "RETURN"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setMode(option)}
                  aria-pressed={mode === option}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    mode === option
                      ? "bg-white text-slate-950 shadow-sm"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  {option === "VALUE" ? "Value" : "Return"}
                </button>
              ))}
            </div>
          </div>
        ) : undefined
      }
    >
      {performance === null ? (
        <StatePanel
          title="Performance unavailable"
          message={
            moduleError ??
            "The portfolio performance module did not return a usable result."
          }
          tone="error"
        />
      ) : performance.points.length === 0 ? (
        <StatePanel
          title="No performance history"
          message="There are no portfolio valuation points for the selected period."
        />
      ) : (
        <div>
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-slate-500">
                Current portfolio value
              </p>
              <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
                {formatCurrency(performance.summary.ending_value, currency)}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <span
                  className={`font-semibold ${signedTone(
                    performance.summary.cumulative_return,
                  )}`}
                >
                  {formatPercent(performance.summary.cumulative_return)} TWR
                </span>
                <span className="text-slate-500">
                  Investment gain/loss {" "}
                  {formatCurrency(
                    performance.summary.investment_gain_loss,
                    currency,
                  )}
                </span>
              </div>
            </div>

            <div className="text-right text-xs leading-5 text-slate-500">
              <p>
                Data as of {formatDateTime(performance.provenance.data_as_of)}
              </p>
              <p>
                Provider {performance.provenance.provider} · {performance.provenance.price_field}
              </p>
            </div>
          </div>

          <Suspense
            fallback={
              <div
                className="h-72 w-full animate-pulse rounded-2xl bg-slate-100 sm:h-80"
                role="status"
                aria-label="Loading performance chart"
              />
            }
          >
            <PerformanceChart
              performance={performance}
              currency={currency}
              mode={mode}
            />
          </Suspense>

          {performance.warnings.length > 0 ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <p className="font-semibold">Data-quality note</p>
              <p className="mt-1 leading-6">
                {performance.warnings[0]?.message}
                {performance.warnings.length > 1
                  ? ` (+${performance.warnings.length - 1} more)`
                  : ""}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </DashboardCard>
  );
}
````

---

# File: `src/features/dashboard/PortfolioSummaryCard.tsx`

````tsx
import { DashboardCard } from "../../components/ui/DashboardCard";
import { DataQualityBadge } from "../../components/ui/DataQualityBadge";
import { StatePanel } from "../../components/ui/StatePanel";
import {
  formatCurrency,
  formatDecimalPercent,
  humanizeCode,
} from "./formatting";
import type {
  DashboardPortfolioSummaryResult,
  PortfolioSummaryUnavailableReason,
} from "../../types/dashboard";

interface PortfolioSummaryCardProps {
  summary: DashboardPortfolioSummaryResult | null;
  currency: string;
  moduleError: string | null;
}

interface SummaryRowProps {
  label: string;
  value: string | null;
  reason?: PortfolioSummaryUnavailableReason | null;
  detail?: string | null;
}

function SummaryRow({ label, value, reason, detail }: SummaryRowProps) {
  return (
    <div className="border-b border-slate-100 py-3 last:border-0">
      <div className="flex items-start justify-between gap-4">
        <dt className="text-sm text-slate-600">{label}</dt>
        <dd className="text-right text-sm font-semibold text-slate-950">
          {value ?? "Not available"}
        </dd>
      </div>
      {reason ? (
        <p className="mt-1 text-right text-xs text-slate-500">
          {humanizeCode(reason)}
        </p>
      ) : detail ? (
        <p className="mt-1 text-right text-xs text-slate-500">{detail}</p>
      ) : null}
    </div>
  );
}

export function PortfolioSummaryCard({
  summary,
  currency,
  moduleError,
}: PortfolioSummaryCardProps) {
  return (
    <DashboardCard
      title="Portfolio summary"
      eyebrow="Accounting"
      actions={
        summary ? <DataQualityBadge quality={summary.data_quality} /> : undefined
      }
    >
      {summary === null ? (
        <StatePanel
          title="Summary unavailable"
          message={
            moduleError ??
            "The portfolio summary module did not return a usable result."
          }
          tone="error"
        />
      ) : (
        <dl>
          <SummaryRow
            label="Total market value"
            value={
              summary.metrics.total_market_value === null
                ? null
                : formatCurrency(summary.metrics.total_market_value, currency)
            }
            reason={summary.metrics.total_market_value_unavailable_reason}
          />
          <SummaryRow
            label="Net contributions"
            value={formatCurrency(summary.metrics.net_contributions, currency)}
          />
          <SummaryRow
            label="Cost basis"
            value={formatCurrency(summary.metrics.cost_basis, currency)}
            detail="Weighted-average analytical book cost"
          />
          <SummaryRow
            label="Cash balance"
            value={formatCurrency(summary.metrics.cash_balance, currency)}
            detail={
              summary.metrics.cash_percentage === null
                ? humanizeCode(summary.metrics.cash_percentage_unavailable_reason)
                : formatDecimalPercent(summary.metrics.cash_percentage)
            }
          />
          <SummaryRow
            label="Unrealized gain/loss"
            value={
              summary.metrics.unrealized_gain_loss === null
                ? null
                : formatCurrency(summary.metrics.unrealized_gain_loss, currency)
            }
            reason={summary.metrics.unrealized_gain_loss_unavailable_reason}
          />
          <SummaryRow
            label="Realized gain/loss"
            value={
              summary.metrics.selected_period_realized_gain_loss === null
                ? null
                : formatCurrency(
                    summary.metrics.selected_period_realized_gain_loss,
                    currency,
                  )
            }
            reason={
              summary.metrics.selected_period_realized_gain_loss_unavailable_reason
            }
          />
          <SummaryRow
            label="Income received"
            value={
              summary.metrics.selected_period_income_received === null
                ? null
                : formatCurrency(
                    summary.metrics.selected_period_income_received,
                    currency,
                  )
            }
            reason={summary.metrics.selected_period_income_unavailable_reason}
          />
        </dl>
      )}
    </DashboardCard>
  );
}
````

---

# File: `src/features/dashboard/ReviewItemsPanel.test.tsx`

````tsx
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type {
    DashboardReviewItem,
    DashboardReviewItemsResult,
} from "../../types/dashboard";
import { ReviewItemsPanel } from "./ReviewItemsPanel";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_A_ID = "00000000-0000-0000-0000-000000000011";
const ASSET_B_ID = "00000000-0000-0000-0000-000000000012";

function reviewItem(
  overrides: Partial<DashboardReviewItem> & Pick<DashboardReviewItem, "key">,
): DashboardReviewItem {
  const { drilldown, ...itemOverrides } = overrides;

  return {
    source: "DAILY_PERFORMANCE",
    severity: "WARNING",
    category: "MARKET_DATA",
    code: "STALE_PRICE_USED",
    message: "A stale market price was used for AAA.",
    ...itemOverrides,
    drilldown: {
      resource: "PERFORMANCE",
      portfolio_id: PORTFOLIO_ID,
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      asset_id: ASSET_A_ID,
      symbol: "AAA",
      observation_date: "2026-09-15",
      ...drilldown,
    },
  };
}

function reviewItemsFixture(): DashboardReviewItemsResult {
  return {
    counts: {
      total: 4,
      by_severity: [
        {
          key: "ERROR",
          count: 1,
        },
        {
          key: "WARNING",
          count: 2,
        },
        {
          key: "INFO",
          count: 1,
        },
      ],
      by_category: [
        {
          key: "MARKET_DATA",
          count: 2,
        },
        {
          key: "DATA_COVERAGE",
          count: 0,
        },
        {
          key: "PROVIDER",
          count: 1,
        },
        {
          key: "VALUATION",
          count: 0,
        },
        {
          key: "ANALYTICS",
          count: 1,
        },
      ],
    },
    filtered_count: 4,
    filters: {
      severity: null,
      category: null,
    },
    items: [
      reviewItem({
        key: "CURRENT_VALUATION:PRICE_PROVIDER_FAILED:AAA:2026-09-15",
        source: "CURRENT_VALUATION",
        severity: "ERROR",
        category: "PROVIDER",
        code: "PRICE_PROVIDER_FAILED",
        message: "The current price provider failed for AAA.",
        drilldown: {
          resource: "HOLDINGS",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: ASSET_A_ID,
          symbol: "AAA",
          observation_date: "2026-09-15",
        },
      }),
      reviewItem({
        key: "DAILY_PERFORMANCE:STALE_PRICE_USED:AAA:2026-09-14",
        source: "DAILY_PERFORMANCE",
        severity: "WARNING",
        category: "MARKET_DATA",
        code: "STALE_PRICE_USED",
        message: "A stale market price was used for AAA on September 14.",
        drilldown: {
          resource: "PERFORMANCE",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: ASSET_A_ID,
          symbol: "AAA",
          observation_date: "2026-09-14",
        },
      }),
      reviewItem({
        key: "DAILY_PERFORMANCE:STALE_PRICE_USED:BBB:2026-09-15",
        source: "DAILY_PERFORMANCE",
        severity: "WARNING",
        category: "MARKET_DATA",
        code: "STALE_PRICE_USED",
        message: "A stale market price was used for BBB on September 15.",
        drilldown: {
          resource: "PERFORMANCE",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: ASSET_B_ID,
          symbol: "BBB",
          observation_date: "2026-09-15",
        },
      }),
      reviewItem({
        key: "ANALYTICS:INSUFFICIENT_HISTORY:PORTFOLIO:2026-09-15",
        source: "ANALYTICS",
        severity: "INFO",
        category: "ANALYTICS",
        code: "INSUFFICIENT_HISTORY",
        message:
          "Some analytics are unavailable because the selected period has insufficient history.",
        drilldown: {
          resource: "ANALYTICS",
          portfolio_id: PORTFOLIO_ID,
          requested_start: "2026-09-01",
          requested_end_exclusive: "2026-09-16",
          asset_id: null,
          symbol: null,
          observation_date: "2026-09-15",
        },
      }),
    ],
    provenance: {
      portfolio_id: PORTFOLIO_ID,
      base_currency: "USD",
      provider: "mock",
      requested_start: "2026-09-01",
      requested_end_exclusive: "2026-09-16",
      effective_start: "2026-09-01",
      effective_end_exclusive: "2026-09-16",
      current_data_as_of: "2026-09-15T21:55:00Z",
      historical_data_as_of: "2026-09-15T21:50:00Z",
      analytics_as_of_date: "2026-09-15",
      calculated_at: "2026-09-15T22:00:00Z",
      engine_version: "0.1.0.dev0",
      included_sources: [
        "CURRENT_VALUATION",
        "DAILY_PERFORMANCE",
        "ANALYTICS",
      ],
      ordering_rule:
        "SEVERITY_THEN_CATEGORY_THEN_CODE_THEN_SYMBOL_DATE_V1",
    },
  };
}

function renderReviewItems(
  result: DashboardReviewItemsResult | null = reviewItemsFixture(),
  {
    isSnapshotComplete = true,
    moduleError = null,
  }: {
    isSnapshotComplete?: boolean;
    moduleError?: string | null;
  } = {},
) {
  render(
    <MemoryRouter
      initialEntries={[
        `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
      ]}
    >
      <ReviewItemsPanel
        reviewItems={result}
        isSnapshotComplete={isSnapshotComplete}
        moduleError={moduleError}
      />
    </MemoryRouter>,
  );
}

describe("ReviewItemsPanel", () => {
  it("renders stable server severity and category counts including zero buckets", () => {
    renderReviewItems();

    const errorFilter = screen.getByRole("button", {
      name: /^Error/i,
    });
    const warningFilter = screen.getByRole("button", {
      name: /^Warning/i,
    });
    const infoFilter = screen.getByRole("button", {
      name: /^Info/i,
    });

    expect(errorFilter).toHaveTextContent("1");
    expect(warningFilter).toHaveTextContent("2");
    expect(infoFilter).toHaveTextContent("1");

    const marketDataFilter = screen.getByRole("button", {
      name: /^Market data/i,
    });
    const dataCoverageFilter = screen.getByRole("button", {
      name: /^Data coverage/i,
    });
    const providerFilter = screen.getByRole("button", {
      name: /^Provider/i,
    });
    const valuationFilter = screen.getByRole("button", {
      name: /^Valuation/i,
    });
    const analyticsFilter = screen.getByRole("button", {
      name: /^Analytics/i,
    });

    expect(marketDataFilter).toHaveTextContent("2");
    expect(dataCoverageFilter).toHaveTextContent("0");
    expect(providerFilter).toHaveTextContent("1");
    expect(valuationFilter).toHaveTextContent("0");
    expect(analyticsFilter).toHaveTextContent("1");

    expect(screen.getByText("4 review items")).toBeInTheDocument();
  });

  it("preserves canonical server item order", () => {
    renderReviewItems();

    const items = screen.getAllByTestId("review-item");

    expect(items).toHaveLength(4);

    expect(items[0]).toHaveAttribute(
      "data-review-item-key",
      "CURRENT_VALUATION:PRICE_PROVIDER_FAILED:AAA:2026-09-15",
    );
    expect(items[1]).toHaveAttribute(
      "data-review-item-key",
      "DAILY_PERFORMANCE:STALE_PRICE_USED:AAA:2026-09-14",
    );
    expect(items[2]).toHaveAttribute(
      "data-review-item-key",
      "DAILY_PERFORMANCE:STALE_PRICE_USED:BBB:2026-09-15",
    );
    expect(items[3]).toHaveAttribute(
      "data-review-item-key",
      "ANALYTICS:INSUFFICIENT_HISTORY:PORTFOLIO:2026-09-15",
    );
  });

  it("filters details without changing server counts or re-ranking matches", () => {
    renderReviewItems();

    const warningFilter = screen.getByRole("button", {
      name: /^Warning/i,
    });

    expect(warningFilter).toHaveTextContent("2");

    fireEvent.click(warningFilter);

    const items = screen.getAllByTestId("review-item");

    expect(items).toHaveLength(2);

    expect(
      within(items[0]!).getByText(
        "A stale market price was used for AAA on September 14.",
      ),
    ).toBeInTheDocument();

    expect(
      within(items[1]!).getByText(
        "A stale market price was used for BBB on September 15.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Showing 2 of 4 server-provided review items."),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: /^Error/i,
      }),
    ).toHaveTextContent("1");

    expect(
      screen.getByRole("button", {
        name: /^Warning/i,
      }),
    ).toHaveTextContent("2");

    expect(
      screen.getByRole("button", {
        name: /^Info/i,
      }),
    ).toHaveTextContent("1");
  });

  it("supports accessible severity and category filter state", () => {
    renderReviewItems();

    const allSeverities = screen.getByRole("button", {
      name: /^All severities/i,
    });
    const warning = screen.getByRole("button", {
      name: /^Warning/i,
    });
    const analytics = screen.getByRole("button", {
      name: /^Analytics/i,
    });

    expect(allSeverities).toHaveTextContent("4");
    expect(allSeverities).toHaveAttribute("aria-pressed", "true");
    expect(warning).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(warning);

    expect(allSeverities).toHaveAttribute("aria-pressed", "false");
    expect(warning).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(analytics);

    expect(analytics).toHaveAttribute("aria-pressed", "true");

    expect(
      screen.getByRole("button", {
        name: "Clear review filters",
      }),
    ).toBeInTheDocument();
  });

  it("preserves dashboard range context in native holding drill-down links", () => {
    renderReviewItems();

    const link = screen.getByRole("link", {
      name: "Open holding",
    });

    expect(link).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/holdings/${ASSET_A_ID}?range=6M`,
    );
  });

  it("renders performance and analytics drill-down context without inventing routes", () => {
    renderReviewItems();

    const items = screen.getAllByTestId("review-item");

    const performanceItem = items[1]!;
    const analyticsItem = items[3]!;

    expect(performanceItem).toHaveTextContent("Performance");
    expect(analyticsItem).toHaveTextContent("Analytics");

    expect(
      within(analyticsItem).getByText("Portfolio-level review item"),
    ).toBeInTheDocument();

    expect(
      screen.getAllByRole("link", {
        name: "Open holding",
      }),
    ).toHaveLength(1);
  });

  it("renders owner-scoped requested period, observation, symbol, and asset context", () => {
    renderReviewItems();

    const firstItem = screen.getAllByTestId("review-item")[0]!;

    expect(firstItem).toHaveTextContent("Holdings");
    expect(firstItem).toHaveTextContent(
      "2026-09-01 to 2026-09-16 (end exclusive)",
    );
    expect(firstItem).toHaveTextContent("2026-09-15");
    expect(firstItem).toHaveTextContent("AAA");
    expect(firstItem).toHaveTextContent(PORTFOLIO_ID);
    expect(firstItem).toHaveTextContent(ASSET_A_ID);
  });

  it("renders calculation and data-as-of provenance without frontend recomputation", () => {
    renderReviewItems();

    expect(screen.getByText(/Requested period:/)).toHaveTextContent(
      "2026-09-01 to 2026-09-16",
    );

    expect(screen.getByText(/Current data as of/)).toBeInTheDocument();
    expect(screen.getByText(/Historical data as of/)).toBeInTheDocument();
    expect(screen.getByText(/Analytics as of/)).toBeInTheDocument();

    expect(screen.getByText(/Provider: mock/)).toBeInTheDocument();
    expect(screen.getByText(/Engine: 0.1.0.dev0/)).toBeInTheDocument();
    expect(screen.getByText(/Base currency: USD/)).toBeInTheDocument();

    expect(
      screen.getByText(
        /Current valuation · Daily performance · Analytics/,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "SEVERITY_THEN_CATEGORY_THEN_CODE_THEN_SYMBOL_DATE_V1",
      ),
    ).toBeInTheDocument();
  });

  it("shows an explicit empty state when the server reports zero review items", () => {
    const result = reviewItemsFixture();

    result.counts = {
      total: 0,
      by_severity: [
        { key: "ERROR", count: 0 },
        { key: "WARNING", count: 0 },
        { key: "INFO", count: 0 },
      ],
      by_category: [
        { key: "MARKET_DATA", count: 0 },
        { key: "DATA_COVERAGE", count: 0 },
        { key: "PROVIDER", count: 0 },
        { key: "VALUATION", count: 0 },
        { key: "ANALYTICS", count: 0 },
      ],
    };
    result.filtered_count = 0;
    result.items = [];

    renderReviewItems(result);

    expect(screen.getByText("No review items")).toBeInTheDocument();

    expect(
      screen.getByText(
        "The current valuation, daily performance, and analytics sources reported no supported data-quality conditions for this selected period.",
      ),
    ).toBeInTheDocument();
  });

  it("shows an explicit no-matches state for a filter combination", () => {
    renderReviewItems();

    fireEvent.click(
      screen.getByRole("button", {
        name: /^Error/i,
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: /^Analytics/i,
      }),
    );

    expect(
      screen.getByText("No matching review items"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "No server-provided review items match the selected severity and category filters.",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Showing 0 of 4 server-provided review items."),
    ).toBeInTheDocument();
  });

  it("clears active filters and restores canonical server detail order", () => {
    renderReviewItems();

    const warningFilter = screen.getByRole("button", {
      name: /^Warning/i,
    });

    expect(warningFilter).toHaveTextContent("2");

    fireEvent.click(warningFilter);

    expect(screen.getAllByTestId("review-item")).toHaveLength(2);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Clear review filters",
      }),
    );

    const items = screen.getAllByTestId("review-item");

    expect(items).toHaveLength(4);

    expect(items[0]).toHaveAttribute(
      "data-review-item-key",
      "CURRENT_VALUATION:PRICE_PROVIDER_FAILED:AAA:2026-09-15",
    );

    expect(items[3]).toHaveAttribute(
      "data-review-item-key",
      "ANALYTICS:INSUFFICIENT_HISTORY:PORTFOLIO:2026-09-15",
    );
  });

  it("keeps available review items visible while labeling a partial dashboard snapshot", () => {
    renderReviewItems(reviewItemsFixture(), {
      isSnapshotComplete: false,
    });

    expect(screen.getByText("Partial snapshot")).toBeInTheDocument();

    expect(
      screen.getByText(
        "This dashboard snapshot is partial because another module is unavailable. The review-item module below remains available with its own calculation and data provenance.",
      ),
    ).toBeInTheDocument();

    expect(screen.getAllByTestId("review-item")).toHaveLength(4);
  });

  it("shows a module-local unavailable state", () => {
    renderReviewItems(null, {
      moduleError:
        "Review items require current valuation, daily performance, and analytics from the shared snapshot context.",
    });

    expect(
      screen.getByText("Review items unavailable"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Review items require current valuation, daily performance, and analytics from the shared snapshot context.",
      ),
    ).toBeInTheDocument();
  });

  it("shows an explicit unavailable state when the module result is null", () => {
    renderReviewItems(null);

    expect(
      screen.getByText("Review items unavailable"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "No data-quality review-item module is available for this dashboard snapshot.",
      ),
    ).toBeInTheDocument();
  });

  it("does not expose unsupported speculative alert categories", () => {
    renderReviewItems();

    expect(screen.queryByText(/account sync/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/classification/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/corporate action/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/allocation drift/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/concentration threshold/i),
    ).not.toBeInTheDocument();
  });
});
````

---

# File: `src/features/dashboard/ReviewItemsPanel.tsx`

````tsx
import { useState } from "react";
import { Link, useLocation } from "react-router";

import { DashboardCard } from "../../components/ui/DashboardCard";
import { StatePanel } from "../../components/ui/StatePanel";
import type {
    DashboardReviewItem,
    DashboardReviewItemsResult,
    ReviewItemCategory,
    ReviewItemSeverity,
} from "../../types/dashboard";
import { formatDate, formatDateTime, humanizeCode } from "./formatting";

interface ReviewItemsPanelProps {
  reviewItems: DashboardReviewItemsResult | null;
  isSnapshotComplete: boolean;
  moduleError: string | null;
}

interface ReviewFilterButtonProps {
  label: string;
  count: number;
  pressed: boolean;
  onClick: () => void;
}

function displayCode(value: string): string {
  return humanizeCode(value) ?? value;
}

function severityClasses(severity: ReviewItemSeverity): string {
  if (severity === "ERROR") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }

  if (severity === "WARNING") {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }

  return "border-blue-200 bg-blue-50 text-blue-800";
}

function severityIcon(severity: ReviewItemSeverity): string {
  if (severity === "ERROR") {
    return "!";
  }

  if (severity === "WARNING") {
    return "▲";
  }

  return "i";
}

function ReviewFilterButton({
  label,
  count,
  pressed,
  onClick,
}: ReviewFilterButtonProps) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
        pressed
          ? "border-slate-900 bg-slate-950 text-white"
          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <span>{label}</span>
      <span
        className={`rounded-full px-1.5 py-0.5 tabular-nums ${
          pressed ? "bg-white/15 text-white" : "bg-slate-100 text-slate-600"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function ReviewItemCard({ item }: { item: DashboardReviewItem }) {
  const location = useLocation();
  const drilldown = item.drilldown;

  const holdingPath =
    drilldown.resource === "HOLDINGS" && drilldown.asset_id !== null
      ? `/portfolios/${encodeURIComponent(
          drilldown.portfolio_id,
        )}/holdings/${encodeURIComponent(drilldown.asset_id)}${location.search}`
      : null;

  return (
    <li
      className="rounded-2xl border border-slate-200 bg-white p-4"
      data-testid="review-item"
      data-review-item-key={item.key}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClasses(
                item.severity,
              )}`}
            >
              <span aria-hidden="true">{severityIcon(item.severity)}</span>
              {displayCode(item.severity)}
            </span>

            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
              {displayCode(item.category)}
            </span>
          </div>

          <p className="mt-3 text-sm font-semibold leading-6 text-slate-950">
            {item.message}
          </p>

          <p className="mt-1 text-xs text-slate-500">
            {displayCode(item.source)} · <code>{item.code}</code>
          </p>
        </div>

        {holdingPath !== null ? (
          <Link
            to={holdingPath}
            className="shrink-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none transition hover:border-blue-200 hover:text-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Open holding
          </Link>
        ) : null}
      </div>

      <dl className="mt-4 grid gap-3 rounded-xl bg-slate-50 p-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="font-medium text-slate-500">Review resource</dt>
          <dd className="mt-1 font-semibold text-slate-900">
            {displayCode(drilldown.resource)}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Requested period</dt>
          <dd className="mt-1 text-slate-700">
            {drilldown.requested_start} to{" "}
            {drilldown.requested_end_exclusive} (end exclusive)
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Observation</dt>
          <dd className="mt-1 text-slate-700">
            {drilldown.observation_date ?? "Not available"}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Asset context</dt>
          <dd className="mt-1 text-slate-700">
            {drilldown.symbol ?? "Portfolio-level review item"}
          </dd>
        </div>

        <div className="sm:col-span-2 lg:col-span-4">
          <dt className="font-medium text-slate-500">Portfolio scope</dt>
          <dd className="mt-1 break-all font-mono text-[11px] text-slate-700">
            {drilldown.portfolio_id}
            {drilldown.asset_id !== null
              ? ` · asset ${drilldown.asset_id}`
              : ""}
          </dd>
        </div>
      </dl>
    </li>
  );
}

function ReviewItemsProvenance({
  reviewItems,
}: {
  reviewItems: DashboardReviewItemsResult;
}) {
  const provenance = reviewItems.provenance;

  return (
    <div className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500">
      <p>
        Requested period: {provenance.requested_start} to{" "}
        {provenance.requested_end_exclusive} (end exclusive) · Effective
        period: {provenance.effective_start} to{" "}
        {provenance.effective_end_exclusive} (end exclusive)
      </p>

      <p>
        Current data as of {formatDateTime(provenance.current_data_as_of)} ·
        Historical data as of{" "}
        {formatDateTime(provenance.historical_data_as_of)} · Analytics as of{" "}
        {formatDate(provenance.analytics_as_of_date)}
      </p>

      <p>
        Calculated {formatDateTime(provenance.calculated_at)} · Provider:{" "}
        {provenance.provider} · Engine: {provenance.engine_version} · Base
        currency: {provenance.base_currency}
      </p>

      <p>
        Sources: {provenance.included_sources.map(displayCode).join(" · ")}
      </p>

      <p className="break-all">
        Ordering: <code>{provenance.ordering_rule}</code>
      </p>
    </div>
  );
}

export function ReviewItemsPanel({
  reviewItems,
  isSnapshotComplete,
  moduleError,
}: ReviewItemsPanelProps) {
  const [severity, setSeverity] = useState<ReviewItemSeverity | null>(null);
  const [category, setCategory] = useState<ReviewItemCategory | null>(null);

  if (moduleError !== null) {
    return (
      <StatePanel
        title="Review items unavailable"
        message={moduleError}
        tone="error"
      />
    );
  }

  if (reviewItems === null) {
    return (
      <StatePanel
        title="Review items unavailable"
        message="No data-quality review-item module is available for this dashboard snapshot."
      />
    );
  }

  // Array.filter preserves the canonical server order.
  const visibleItems = reviewItems.items.filter(
    (item) =>
      (severity === null || item.severity === severity) &&
      (category === null || item.category === category),
  );

  const hasFilters = severity !== null || category !== null;

  return (
    <DashboardCard
      title="Data-quality review"
      eyebrow="Review items"
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {!isSnapshotComplete ? (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
              Partial snapshot
            </span>
          ) : null}

          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
            {reviewItems.counts.total} review items
          </span>
        </div>
      }
    >
      <p className="text-sm leading-6 text-slate-600">
        Counts and item order come from the snapshot review-items contract.
        Filters only narrow the returned details; they do not create alerts,
        recompute server counts, or change canonical order.
      </p>

      {!isSnapshotComplete ? (
        <div
          className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          role="status"
        >
          This dashboard snapshot is partial because another module is
          unavailable. The review-item module below remains available with its
          own calculation and data provenance.
        </div>
      ) : null}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <fieldset>
          <legend className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Severity
          </legend>

          <div className="mt-2 flex flex-wrap gap-2">
            <ReviewFilterButton
              label="All severities"
              count={reviewItems.counts.total}
              pressed={severity === null}
              onClick={() => setSeverity(null)}
            />

            {reviewItems.counts.by_severity.map((count) => (
              <ReviewFilterButton
                key={count.key}
                label={displayCode(count.key)}
                count={count.count}
                pressed={severity === count.key}
                onClick={() => setSeverity(count.key)}
              />
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Category
          </legend>

          <div className="mt-2 flex flex-wrap gap-2">
            <ReviewFilterButton
              label="All categories"
              count={reviewItems.counts.total}
              pressed={category === null}
              onClick={() => setCategory(null)}
            />

            {reviewItems.counts.by_category.map((count) => (
              <ReviewFilterButton
                key={count.key}
                label={displayCode(count.key)}
                count={count.count}
                pressed={category === count.key}
                onClick={() => setCategory(count.key)}
              />
            ))}
          </div>
        </fieldset>
      </div>

      {hasFilters ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
          <p aria-live="polite">
            Showing {visibleItems.length} of {reviewItems.counts.total}{" "}
            server-provided review items.
          </p>

          <button
            type="button"
            onClick={() => {
              setSeverity(null);
              setCategory(null);
            }}
            className="font-semibold text-blue-700 underline decoration-blue-200 underline-offset-4 outline-none hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Clear review filters
          </button>
        </div>
      ) : null}

      <div className="mt-5">
        {reviewItems.counts.total === 0 ? (
          <StatePanel
            title="No review items"
            message="The current valuation, daily performance, and analytics sources reported no supported data-quality conditions for this selected period."
          />
        ) : visibleItems.length === 0 ? (
          <StatePanel
            title="No matching review items"
            message="No server-provided review items match the selected severity and category filters."
          />
        ) : (
          <ol
            className="space-y-3"
            aria-label="Data-quality review items"
          >
            {visibleItems.map((item) => (
              <ReviewItemCard key={item.key} item={item} />
            ))}
          </ol>
        )}
      </div>

      <ReviewItemsProvenance reviewItems={reviewItems} />
    </DashboardCard>
  );
}
````

---

# File: `src/hooks/useAuth.ts`

````typescript
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import {
  fetchAuthSession,
  loginWithPassword,
  logoutSession,
  type AuthSessionResult,
  type LoginRequest,
} from "../api/auth";

export const AUTH_SESSION_QUERY_KEY = ["auth","session"] as const;

function clearOwnerScopedQueries(queryClient: QueryClient) {
  queryClient.removeQueries({
    predicate: (query) => {
      const root = query.queryKey[0];
      return (
        root === "portfolios" ||
        (typeof root === "string" && root.startsWith("portfolio-"))
      );
    },
  });
}

export function useSession() {
  return useQuery({
    queryKey: AUTH_SESSION_QUERY_KEY,
    queryFn: ({ signal }) => fetchAuthSession(signal),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: LoginRequest) => loginWithPassword(request),
    onSuccess: (session: AuthSessionResult) => {
      clearOwnerScopedQueries(queryClient);
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, session);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => logoutSession(),
    onSuccess: (session: AuthSessionResult) => {
      clearOwnerScopedQueries(queryClient);
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, session);
    },
  });
}
````

---

# File: `src/hooks/usePortfolioData.ts`

````typescript
import { useQuery } from "@tanstack/react-query";

import {
  fetchDashboardSnapshot,
  fetchPortfolioAnalytics,
  fetchPortfolios,
  type DashboardSnapshotRequest,
  type PortfolioAnalyticsRequest,
} from "../api/portfolios";

export function usePortfolios() {
  return useQuery({
    queryKey: ["portfolios"],
    queryFn: ({ signal }) => fetchPortfolios(signal),
    staleTime: 30_000,
  });
}

export function useDashboardSnapshot(
  request: DashboardSnapshotRequest | null,
) {
  return useQuery({
    queryKey:
      request === null
        ? ["portfolio-dashboard", "disabled"]
        : [
            "portfolio-dashboard",
            request.portfolioId,
            request.start,
            request.end,
          ],
    queryFn: ({ signal }) => {
      if (request === null) {
        throw new Error("Dashboard snapshot request is not available.");
      }

      return fetchDashboardSnapshot(request, signal);
    },
    enabled: request !== null,
    retry: 1,
    staleTime: 30_000,
  });
}

export function usePortfolioAnalytics(
  request: PortfolioAnalyticsRequest | null,
) {
  return useQuery({
    queryKey:
      request === null
        ? ["portfolio-analysis", "disabled"]
        : [
            "portfolio-analysis",
            request.portfolioId,
            request.start,
            request.end,
            request.rollingWindow ?? null,
          ],
    queryFn: ({ signal }) => {
      if (request === null) {
        throw new Error("Portfolio analysis request is not available.");
      }

      return fetchPortfolioAnalytics(request, signal);
    },
    enabled: request !== null,
    retry: 1,
    staleTime: 30_000,
  });
}
````

---

# File: `src/index.css`

````css
@import "tailwindcss";

:root {
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  color: #0f172a;
  background: #f8fafc;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

html {
  min-width: 320px;
  min-height: 100%;
  background: #f8fafc;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background: #f8fafc;
}

button,
select,
summary,
a {
  -webkit-tap-highlight-color: transparent;
}

button,
select,
a {
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
````

---

# File: `src/layouts/DashboardShell.tsx`

````tsx
import type { PropsWithChildren, ReactNode } from "react";
import { Link, useNavigate } from "react-router";

import { useLogout, useSession } from "../hooks/useAuth";

interface DashboardShellProps extends PropsWithChildren {
  header: ReactNode;
}

function OverviewIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M4 13h6V4H4v9Zm0 7h6v-4H4v4Zm10 0h6v-9h-6v9Zm0-12h6V4h-6v4Z" />
    </svg>
  );
}

export function DashboardShell({ header, children }: DashboardShellProps) {
  const navigate = useNavigate();
  const sessionQuery = useSession();
  const logoutMutation = useLogout();
  const user = sessionQuery.data?.user;

  async function handleLogout() {
    try {
      await logoutMutation.mutateAsync();
      navigate("/login", { replace: true });
    } catch {
      // The visible error text below keeps the current protected view intact.
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-20 border-r border-slate-800 bg-slate-950 md:flex md:flex-col md:items-center">
        <Link
          to="/"
          className="mt-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-sm font-bold text-white shadow-lg shadow-blue-950/30"
          aria-label="Portfolio Intelligence home"
        >
          PI
        </Link>
        <nav className="mt-10" aria-label="Primary navigation">
          <Link
            to="/"
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-800 text-white outline-none transition hover:bg-slate-700 focus-visible:ring-2 focus-visible:ring-blue-400"
            aria-label="Overview"
            title="Overview"
          >
            <OverviewIcon />
          </Link>
        </nav>
      </aside>

      <div className="md:pl-20">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="border-b border-slate-100 bg-slate-50/90">
            <div className="mx-auto flex min-h-9 w-full max-w-[1600px] items-center justify-end gap-3 px-4 py-1.5 text-xs sm:px-6 lg:px-8">
              {user ? (
                <span className="max-w-56 truncate text-slate-500" title={user.email}>
                  {user.first_name || user.last_name
                    ? `${user.first_name} ${user.last_name}`.trim()
                    : user.email}
                </span>
              ) : null}
              <button
                type="button"
                onClick={() => void handleLogout()}
                disabled={logoutMutation.isPending}
                className="font-semibold text-slate-700 outline-none hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
              >
                {logoutMutation.isPending ? "Signing out…" : "Sign out"}
              </button>
              {logoutMutation.error instanceof Error ? (
                <span role="alert" className="text-rose-700">
                  Sign out failed.
                </span>
              ) : null}
            </div>
          </div>
          {header}
        </header>
        <main className="mx-auto w-full max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          {children}
        </main>
      </div>
    </div>
  );
}
````

---

# File: `src/main.tsx`

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import "./index.css";

const queryClient = new QueryClient();
const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("Root element #root was not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
````

---

# File: `src/pages/DashboardPage.test.tsx`

````tsx
import {
    QueryClient,
    QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import {
    MemoryRouter,
    Route,
    Routes,
} from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { DashboardPage } from "./DashboardPage";

const PORTFOLIO_ID =
  "00000000-0000-0000-0000-000000000002";

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
    },
  });

  return queryClient;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe(
  "DashboardPage portfolio analysis navigation",
  () => {
    it("preserves the selected portfolio and range in the analysis link", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn((input: RequestInfo | URL) => {
          const url = String(input);

          if (url.endsWith("/api/v1/portfolios/")) {
            return Promise.resolve(
              new Response(
                JSON.stringify([
                  {
                    id: PORTFOLIO_ID,
                    name: "Primary portfolio",
                    base_currency: "USD",
                    benchmark_asset_id: null,
                    created_at:
                      "2025-01-02T15:00:00Z",
                    updated_at:
                      "2026-09-15T22:00:00Z",
                  },
                ]),
                {
                  status: 200,
                  headers: {
                    "content-type":
                      "application/json",
                  },
                },
              ),
            );
          }

          if (
            url.includes(
              `/api/v1/portfolios/${PORTFOLIO_ID}/dashboard/`,
            )
          ) {
            return new Promise<Response>(
              () => undefined,
            );
          }

          throw new Error(
            `Unexpected request: ${url}`,
          );
        }),
      );

      const queryClient =
        createTestQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter
            initialEntries={[
              `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
            ]}
          >
            <Routes>
              <Route
                path="/portfolios/:portfolioId/dashboard"
                element={<DashboardPage />}
              />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      );

      expect(
        await screen.findByRole("link", {
          name: "View portfolio analysis →",
        }),
      ).toHaveAttribute(
        "href",
        `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
      );
    });
  },
);
````

---

# File: `src/pages/DashboardPage.tsx`

````tsx
import { useMemo, type ChangeEvent } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";

import { StatePanel } from "../components/ui/StatePanel";
import { DashboardOverview } from "../features/dashboard/DashboardOverview";
import {
  DASHBOARD_RANGES,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import { formatDateTime } from "../features/dashboard/formatting";
import {
  useDashboardSnapshot,
  usePortfolios,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type { PerformanceDataQuality } from "../types/dashboard";

function isDashboardRange(
  value: string | null,
): value is DashboardRange {
  return (
    value !== null &&
    DASHBOARD_RANGES.includes(value as DashboardRange)
  );
}

function snapshotQuality(
  quality: PerformanceDataQuality | undefined,
  isComplete: boolean | undefined,
): { label: string; className: string } {
  if (quality === "STALE") {
    return {
      label: "Stale data",
      className:
        "border-amber-200 bg-amber-50 text-amber-900",
    };
  }

  if (quality === "PARTIAL" || isComplete === false) {
    return {
      label: "Partial data",
      className:
        "border-orange-200 bg-orange-50 text-orange-900",
    };
  }

  if (quality === "UNAVAILABLE") {
    return {
      label: "Unavailable",
      className:
        "border-rose-200 bg-rose-50 text-rose-900",
    };
  }

  return {
    label: "Current",
    className:
      "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
}

export function DashboardPage() {
  const { portfolioId } = useParams<{
    portfolioId: string;
  }>();

  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const portfoliosQuery = usePortfolios();

  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );

  const rangeParam = searchParams.get("range");

  const range: DashboardRange = isDashboardRange(rangeParam)
    ? rangeParam
    : "1M";

  const request = useMemo(() => {
    if (!portfolioId || !selectedPortfolio) {
      return null;
    }

    const dates = resolveDashboardDateRange(
      range,
      selectedPortfolio.created_at,
    );

    return {
      portfolioId,
      start: dates.start,
      end: dates.end,
    };
  }, [portfolioId, range, selectedPortfolio]);

  const snapshotQuery = useDashboardSnapshot(request);
  const snapshot = snapshotQuery.data;

  const freshness = snapshotQuality(
    snapshot?.performance?.portfolio_data_quality,
    snapshot?.is_complete,
  );

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link to="/" className="hover:text-slate-900">
            Overview
          </Link>
          <span aria-hidden="true">/</span>
          <span>Portfolio dashboard</span>
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
            {selectedPortfolio?.name ?? "Portfolio dashboard"}
          </h1>

          {snapshot ? (
            <span
              className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${freshness.className}`}
            >
              {freshness.label}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex w-full flex-wrap items-center justify-end gap-3 sm:w-auto">
        {portfoliosQuery.data &&
        portfoliosQuery.data.length > 0 ? (
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <span className="sr-only">Portfolio</span>

            <select
              value={portfolioId ?? ""}
              onChange={(
                event: ChangeEvent<HTMLSelectElement>,
              ) => {
                if (event.target.value) {
                  navigate(
                    `/portfolios/${event.target.value}/dashboard?range=${range}`,
                  );
                }
              }}
              className="max-w-52 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              {portfoliosQuery.data.map((portfolio) => (
                <option
                  key={portfolio.id}
                  value={portfolio.id}
                >
                  {portfolio.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {snapshot ? (
          <div className="text-right text-xs leading-5 text-slate-500">
            <p>
              {snapshot.snapshot.base_currency} ·{" "}
              {snapshot.snapshot.provider}
            </p>
            <p>
              As of{" "}
              {formatDateTime(
                snapshot.snapshot.current_data_as_of,
              )}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <section
        className="mb-5 flex flex-wrap items-center justify-between gap-4"
        aria-label="Dashboard period controls"
      >
        <div>
          <p className="text-sm font-medium text-slate-500">
            Selected period
          </p>

          <p className="mt-0.5 text-sm text-slate-700">
            {snapshot
              ? `${snapshot.snapshot.effective_start} to ${snapshot.snapshot.effective_end_exclusive}`
              : "Waiting for portfolio snapshot"}
          </p>

          {portfolioId && selectedPortfolio ? (
            <Link
              to={`/portfolios/${encodeURIComponent(
                portfolioId,
              )}/analysis?range=${encodeURIComponent(range)}`}
              className="mt-2 inline-flex text-sm font-semibold text-blue-700 outline-none underline decoration-blue-200 underline-offset-4 hover:text-blue-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              View portfolio analysis →
            </Link>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
          {DASHBOARD_RANGES.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={range === option}
              onClick={() => {
                const next = new URLSearchParams(
                  searchParams,
                );
                next.set("range", option);
                setSearchParams(next);
              }}
              className={`rounded-xl px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                range === option
                  ? "bg-slate-950 text-white"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              {option === "ALL" ? "All" : option}
            </button>
          ))}
        </div>
      </section>

      {!portfoliosQuery.isPending &&
      portfoliosQuery.data &&
      !selectedPortfolio ? (
        <StatePanel
          title="Portfolio not found"
          message="This portfolio is not available in the authenticated account scope."
          tone="error"
          action={
            <Link
              to="/"
              className="inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Choose a portfolio
            </Link>
          }
        />
      ) : (
        <DashboardOverview
          snapshot={snapshot}
          isLoading={
            snapshotQuery.isPending ||
            portfoliosQuery.isPending
          }
          isFetching={
            snapshotQuery.isFetching &&
            snapshot !== undefined
          }
          error={
            snapshotQuery.error instanceof Error
              ? snapshotQuery.error
              : portfoliosQuery.error instanceof Error
                ? portfoliosQuery.error
                : null
          }
          onRetry={() => {
            void portfoliosQuery.refetch();
            void snapshotQuery.refetch();
          }}
        />
      )}

      {snapshot ? (
        <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-slate-500">
          <p>
            Snapshot {snapshot.snapshot.snapshot_id} ·
            Engine {snapshot.snapshot.engine_version}
          </p>

          <p>
            Calculated{" "}
            {formatDateTime(
              snapshot.snapshot.calculated_at,
            )}
          </p>
        </footer>
      ) : null}
    </DashboardShell>
  );
}
````

---

# File: `src/pages/HoldingDetailPage.test.tsx`

````tsx
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import { HoldingDetailPage } from "./HoldingDetailPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";
const ASSET_ID = "00000000-0000-0000-0000-000000000012";

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
    },
  });

  return queryClient;
}

describe("HoldingDetailPage", () => {
  it("preserves the selected portfolio and time-range context", () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter
          initialEntries={[
            {
              pathname: `/portfolios/${PORTFOLIO_ID}/holdings/${ASSET_ID}`,
              search: "?range=6M",
              state: {
                holding: {
                  assetId: ASSET_ID,
                  symbol: "BBB",
                  name: "BBB Incorporated",
                  assetType: "STOCK",
                  currency: "USD",
                },
              },
            },
          ]}
        >
          <Routes>
            <Route
              path="/portfolios/:portfolioId/holdings/:assetId"
              element={<HoldingDetailPage />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "BBB" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("BBB Incorporated"),
    ).toBeInTheDocument();
    expect(screen.getByText("Range 6M")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "← Back to portfolio dashboard",
      }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );
  });
});
````

---

# File: `src/pages/HoldingDetailPage.tsx`

````tsx
import { Link, useLocation, useParams, useSearchParams } from "react-router";

import { DashboardShell } from "../layouts/DashboardShell";

interface HoldingRouteState {
  holding?: {
    assetId: string;
    symbol: string;
    name: string;
    assetType: string;
    currency: string;
  };
}

export function HoldingDetailPage() {
  const { portfolioId, assetId } = useParams<{
    portfolioId: string;
    assetId: string;
  }>();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const state = location.state as HoldingRouteState | null;
  const holding = state?.holding;
  const range = searchParams.get("range") ?? "1M";
  const preservedSearch = location.search || `?range=${encodeURIComponent(range)}`;
  const backPath = portfolioId
    ? `/portfolios/${encodeURIComponent(portfolioId)}/dashboard${preservedSearch}`
    : "/";
  const title = holding?.symbol ?? "Holding detail";

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link to={backPath} className="hover:text-slate-900">
            Portfolio dashboard
          </Link>
          <span aria-hidden="true">/</span>
          <span>Holding detail</span>
        </div>
        <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          {title}
        </h1>
      </div>
      <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
        Range {range}
      </span>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <div className="mx-auto max-w-4xl">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
            Detail route shell
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
            {holding?.name ?? "Security holding"}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {holding
              ? `${holding.assetType} · ${holding.currency}`
              : `Asset ${assetId ?? "unknown"}`}
          </p>

          <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-700">
            <p className="font-semibold text-slate-950">Context preserved</p>
            <p className="mt-1 leading-6">
              Returning to the dashboard preserves portfolio {portfolioId ?? "unknown"} and
              the selected {range} time-range context. Detailed security analytics are
              intentionally deferred to a later Phase 4 holding-detail batch.
            </p>
          </div>

          <Link
            to={backPath}
            className="mt-6 inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            ← Back to portfolio dashboard
          </Link>
        </section>
      </div>
    </DashboardShell>
  );
}
````

---

# File: `src/pages/HomePage.tsx`

````tsx
import { Link } from "react-router";

import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import { DashboardShell } from "../layouts/DashboardShell";
import { usePortfolios } from "../hooks/usePortfolioData";

export function HomePage() {
  const portfoliosQuery = usePortfolios();
  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] items-center px-4 py-3 sm:px-6 lg:px-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
          Portfolio Intelligence
        </p>
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          Overview
        </h1>
      </div>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 max-w-2xl">
          <p className="text-sm font-semibold text-blue-700">Portfolio analytics</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Select a portfolio
          </h2>
          <p className="mt-3 text-base leading-7 text-slate-600">
            Open a coherent dashboard snapshot with portfolio value, selected-period
            performance, accounting context, and data freshness from the backend.
          </p>
        </div>

        {portfoliosQuery.isPending ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, index) => (
              <Skeleton key={index} className="h-36 w-full" />
            ))}
          </div>
        ) : portfoliosQuery.error instanceof Error ? (
          <StatePanel
            title="Portfolios could not load"
            message={portfoliosQuery.error.message}
            tone="error"
            action={
              <button
                type="button"
                onClick={() => void portfoliosQuery.refetch()}
                className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
              >
                Retry
              </button>
            }
          />
        ) : portfoliosQuery.data?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {portfoliosQuery.data.map((portfolio) => (
              <Link
                key={portfolio.id}
                to={`/portfolios/${portfolio.id}/dashboard?range=1M`}
                className="group rounded-3xl border border-slate-200 bg-white p-5 shadow-sm outline-none transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  {portfolio.base_currency} portfolio
                </p>
                <h3 className="mt-2 text-lg font-semibold text-slate-950 group-hover:text-blue-700">
                  {portfolio.name}
                </h3>
                <p className="mt-6 text-sm font-semibold text-blue-700">
                  Open dashboard →
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <StatePanel
            title="No portfolios yet"
            message="No owned portfolios are available for this account. Portfolio creation and transaction entry remain separate Phase 4 workflows."
          />
        )}
      </div>
    </DashboardShell>
  );
}
````

---

# File: `src/pages/LoginPage.test.tsx`

````tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

import { LoginPage } from "./LoginPage";

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/login",
            state: {
              from: "/portfolios/portfolio-1/dashboard?range=3M",
            },
          },
        ]}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/portfolios/:portfolioId/dashboard"
            element={<h1>Returned dashboard</h1>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("successful login returns to the originally requested protected URL", async () => {
  document.cookie = "csrftoken=login-test-token; path=/";
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.endsWith("/api/v1/auth/session/")) {
      return new Response(
        JSON.stringify({ authenticated: false, user: null }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      );
    }

    if (url.endsWith("/api/v1/auth/login/")) {
      return new Response(
        JSON.stringify({
          authenticated: true,
          user: {
            id: "00000000-0000-0000-0000-000000000001",
            email: "owner@example.com",
            first_name: "Portfolio",
            last_name: "Owner",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  renderLogin();

  fireEvent.change(await screen.findByLabelText("Email"), {
    target: { value: "owner@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "secret-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(
    await screen.findByRole("heading", { name: "Returned dashboard" }),
  ).toBeInTheDocument();
});
````

---

# File: `src/pages/LoginPage.tsx`

````tsx
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import { useLogin, useSession } from "../hooks/useAuth";

interface LoginLocationState {
  from?: unknown;
}

function safeReturnTo(state: unknown): string {
  if (state === null || typeof state !== "object") {
    return "/";
  }

  const from = (state as LoginLocationState).from;
  if (
    typeof from !== "string" ||
    !from.startsWith("/") ||
    from.startsWith("//") ||
    from.startsWith("/login")
  ) {
    return "/";
  }

  return from;
}

export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const sessionQuery = useSession();
  const loginMutation = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const returnTo = safeReturnTo(location.state);

  if (sessionQuery.data?.authenticated) {
    return <Navigate to={returnTo} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      await loginMutation.mutateAsync({ email, password });
      navigate(returnTo, { replace: true });
    } catch {
      // Mutation state renders the stable API error below.
    }
  }

  const loginError =
    loginMutation.error instanceof ApiError
      ? loginMutation.error.message
      : loginMutation.error instanceof Error
        ? loginMutation.error.message
        : null;

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-12 text-slate-950 sm:px-6">
      <section className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl shadow-black/30 sm:p-8">
        <div className="mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-sm font-bold text-white">
            PI
          </div>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
            Portfolio Intelligence
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Sign in
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Use the email and password for your Portfolio Intelligence account.
          </p>
        </div>

        {sessionQuery.error instanceof Error ? (
          <div
            role="alert"
            className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
          >
            Secure session setup failed. {sessionQuery.error.message}
            <button
              type="button"
              onClick={() => void sessionQuery.refetch()}
              className="ml-2 font-semibold underline underline-offset-2"
            >
              Retry
            </button>
          </div>
        ) : null}

        {loginError ? (
          <div
            role="alert"
            className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
          >
            {loginError}
          </div>
        ) : null}

        <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)}>
          <label className="block">
            <span className="text-sm font-semibold text-slate-800">Email</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-base outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-800">Password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-base outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <button
            type="submit"
            disabled={
              sessionQuery.isPending ||
              sessionQuery.isError ||
              loginMutation.isPending
            }
            className="inline-flex w-full items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white outline-none transition hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loginMutation.isPending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
````

---

# File: `src/pages/PortfolioAnalysisPage.test.tsx`

````tsx
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import {
  MemoryRouter,
  Route,
  Routes,
} from "react-router";

import { AUTH_SESSION_QUERY_KEY } from "../hooks/useAuth";
import type { PortfolioAnalyticsResult } from "../types/analytics";
import { PortfolioAnalysisPage } from "./PortfolioAnalysisPage";

const PORTFOLIO_ID = "00000000-0000-0000-0000-000000000002";

function createTestQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        retryDelay: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

  queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, {
    authenticated: true,
    user: {
      id: "00000000-0000-0000-0000-000000000100",
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
    },
  });

  return queryClient;
}

function portfolioListResponse(): Response {
  return new Response(
    JSON.stringify([
      {
        id: PORTFOLIO_ID,
        name: "Primary portfolio",
        base_currency: "USD",
        benchmark_asset_id: "00000000-0000-0000-0000-000000000090",
        created_at: "2025-01-02T15:00:00Z",
        updated_at: "2026-09-15T22:00:00Z",
      },
    ]),
    {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    },
  );
}

function analyticsFixture(): PortfolioAnalyticsResult {
  return {
    portfolio_id: PORTFOLIO_ID,
    observations: 42,
    benchmark_observations: 40,
    cumulative_return: 0.125,
    cagr: {
      value: 0.14,
      wealth_ratio: 1.125,
      elapsed_days: 300,
      elapsed_years: 0.821,
      is_short_period: true,
    },
    annualized_volatility: 0.18,
    sharpe: {
      value: 0.78,
      observations: 42,
      risk_free_rate_annual: 0,
      risk_free_rate_daily: 0,
      annualization_factor: 252,
      warnings: [],
    },
    sortino: {
      value: 1.12,
      observations: 42,
      minimum_acceptable_return_annual: 0,
      minimum_acceptable_return_daily: 0,
      downside_deviation: 0.11,
      annualization_factor: 252,
      warnings: [],
    },
    maximum_drawdown: {
      value: -0.09,
      observations: 42,
      peak_index: 12,
      trough_index: 18,
      warnings: [],
    },
    beta: {
      value: 0.91,
      observations: 40,
      warnings: [],
    },
    benchmark_correlation: {
      value: 0.98,
      observations: 40,
      warnings: [],
    },
    current_allocation: {
      positions: [
        {
          asset_id: "00000000-0000-0000-0000-000000000011",
          market_value: 900,
          weight: 0.9,
        },
      ],
      cash_value: 100,
      cash_weight: 0.1,
      total_market_value: 1000,
      weight_sum: 1,
      weight_sum_tolerance: 1e-8,
    },
    concentration: {
      largest_position_weight: 0.9,
      herfindahl_hirschman_index: 0.81,
      security_position_count: 1,
      cash_weight: 0.1,
      largest_position_includes_cash: false,
      hhi_includes_cash: false,
      long_only: true,
      weight_sum_tolerance: 1e-8,
    },
    rolling_return_window: null,
    rolling_returns: [],
    provenance: {
      engine_version: "0.1.0.dev0",
      as_of_date: "2026-09-15",
      period_start: "2026-08-01",
      period_end: "2026-09-15",
      data_source: "mock",
      price_field: "adjusted_close",
      annualization_factor: 252,
      benchmark: "SPY",
      assumptions: [
        "historical returns use adjusted_close",
        "current allocation uses raw close",
        "benchmark correlation uses Pearson correlation on exact date intersections",
        "risk_free_rate_annual=0.0",
        "minimum_acceptable_return_annual=0.0",
      ],
      warnings: [],
    },
    warnings: [],
  };
}

function analyticsFixtureWithRolling(): PortfolioAnalyticsResult {
  const analytics = analyticsFixture();

  analytics.rolling_return_window = 20;
  analytics.rolling_returns = [
    {
      period_end: "2026-09-10",
      value: 0.035,
    },
    {
      period_end: "2026-09-15",
      value: 0.045,
    },
  ];
  analytics.provenance.assumptions.push(
    "rolling_return_window_observations=20",
  );

  return analytics;
}

function renderPage(
  initialEntry = `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
) {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/portfolios/:portfolioId/analysis"
            element={<PortfolioAnalysisPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function installSuccessfulFetch(
  analytics = analyticsFixture(),
) {
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/v1/portfolios/")) {
        return portfolioListResponse();
      }

      if (
        url.includes(
          `/api/v1/analytics/portfolios/${PORTFOLIO_ID}/`,
        )
      ) {
        return new Response(JSON.stringify(analytics), {
          status: 200,
          headers: {
            "content-type": "application/json",
          },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    },
  );

  vi.stubGlobal("fetch", fetchMock);

  return fetchMock;
}

function installAnalyticsError(
  status: number,
  payload: {
    code: string;
    detail: string;
  },
) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith("/api/v1/portfolios/")) {
        return portfolioListResponse();
      }

      if (
        url.includes(
          `/api/v1/analytics/portfolios/${PORTFOLIO_ID}/`,
        )
      ) {
        return new Response(JSON.stringify(payload), {
          status,
          headers: {
            "content-type": "application/json",
          },
        });
      }

      throw new Error(`Unexpected request: ${url}`);
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PortfolioAnalysisPage", () => {
  it("uses the explicit PortfolioAnalyticsResult transport contract", () => {
    const analytics = analyticsFixture();

    expectTypeOf(analytics).toMatchTypeOf<PortfolioAnalyticsResult>();

    expectTypeOf<
      PortfolioAnalyticsResult["cumulative_return"]
    >().toEqualTypeOf<number | null>();

    expectTypeOf<
      PortfolioAnalyticsResult["benchmark_observations"]
    >().toEqualTypeOf<number | null>();

    expectTypeOf<
      PortfolioAnalyticsResult["benchmark_correlation"]
    >().toMatchTypeOf<
      | {
          value: number | null;
          observations: number;
          warnings: { code: string; message: string }[];
        }
      | null
    >();

    expectTypeOf<
      PortfolioAnalyticsResult["rolling_return_window"]
    >().toEqualTypeOf<number | null>();
  });

  it("renders backend-provided analytics values without recomputing them", async () => {
    installSuccessfulFetch();
    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: "Analytical results",
      }),
    ).toBeInTheDocument();

    const cumulativeReturn = screen
      .getByText("Cumulative return")
      .closest("article");
    const cagr = screen.getByText("CAGR").closest("article");
    const volatility = screen
      .getByText("Annualized volatility")
      .closest("article");
    const sharpe = screen
      .getByText("Sharpe ratio")
      .closest("article");
    const sortino = screen
      .getByText("Sortino ratio")
      .closest("article");
    const downside = screen
      .getByText("Downside deviation")
      .closest("article");
    const drawdown = screen
      .getByText("Maximum drawdown")
      .closest("article");
    const beta = screen.getByText("Beta").closest("article");

    expect(cumulativeReturn).not.toBeNull();
    expect(cagr).not.toBeNull();
    expect(volatility).not.toBeNull();
    expect(sharpe).not.toBeNull();
    expect(sortino).not.toBeNull();
    expect(downside).not.toBeNull();
    expect(drawdown).not.toBeNull();
    expect(beta).not.toBeNull();

    expect(
      within(cumulativeReturn!).getByText("+12.50%"),
    ).toBeInTheDocument();
    expect(within(cagr!).getByText("+14.00%")).toBeInTheDocument();
    expect(
      within(volatility!).getByText("18.00%"),
    ).toBeInTheDocument();
    expect(within(sharpe!).getByText("0.78")).toBeInTheDocument();
    expect(within(sortino!).getByText("1.12")).toBeInTheDocument();
    expect(
      within(downside!).getByText("11.00%"),
    ).toBeInTheDocument();
    expect(
      within(drawdown!).getByText("-9.00%"),
    ).toBeInTheDocument();
    expect(within(beta!).getByText("0.91")).toBeInTheDocument();

    expect(screen.getByText("$1,000.00")).toBeInTheDocument();
    expect(screen.getByText("Security-only HHI")).toBeInTheDocument();
    expect(screen.getByText("0.810")).toBeInTheDocument();
  });

  it("renders server-provided benchmark correlation", async () => {
    installSuccessfulFetch();
    renderPage();

    const label = await screen.findByText("Benchmark correlation");
    const card = label.closest("article");

    expect(card).not.toBeNull();
    expect(within(card!).getByText("0.98")).toBeInTheDocument();
    expect(
      within(card!).getByText("40 aligned observations"),
    ).toBeInTheDocument();
  });

  it("renders explicit Not available values with associated server diagnostics", async () => {
    const analytics = analyticsFixture();

    analytics.annualized_volatility = null;
    analytics.sharpe = null;
    analytics.sortino = null;
    analytics.beta = null;
    analytics.benchmark_correlation = null;
    analytics.benchmark_observations = null;

    analytics.warnings = [
      {
        code: "INSUFFICIENT_HISTORY",
        message:
          "Volatility, Sharpe, and Sortino require at least 30 daily return observations.",
        observations: 12,
      },
      {
        code: "BENCHMARK_NOT_CONFIGURED",
        message: "Portfolio has no configured benchmark asset.",
        observations: null,
      },
    ];

    analytics.provenance.benchmark = null;
    analytics.provenance.warnings = analytics.warnings.map(
      (warning) => warning.message,
    );

    installSuccessfulFetch(analytics);
    renderPage();

    expect(
      await screen.findByText("Limited history"),
    ).toBeInTheDocument();

    const volatility = screen
      .getByText("Annualized volatility")
      .closest("article");
    const sharpe = screen
      .getByText("Sharpe ratio")
      .closest("article");
    const beta = screen.getByText("Beta").closest("article");
    const correlation = screen
      .getByText("Benchmark correlation")
      .closest("article");

    expect(
      within(volatility!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(sharpe!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(beta!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(correlation!).getByText("Not available"),
    ).toBeInTheDocument();

    expect(
      within(volatility!).getByText(
        /require at least 30 daily return observations/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(beta!).getByText(
        "Portfolio has no configured benchmark asset.",
      ),
    ).toBeInTheDocument();
    expect(
      within(correlation!).getByText(
        "Portfolio has no configured benchmark asset.",
      ),
    ).toBeInTheDocument();
  });

  it("renders server-calculated rolling returns without client recomputation", async () => {
    installSuccessfulFetch(analyticsFixtureWithRolling());

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M&rollingWindow=20`,
    );

    expect(
      await screen.findByRole("heading", {
        name: "Rolling returns",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("20-observation window"),
    ).toBeInTheDocument();
    expect(screen.getByText("+3.50%")).toBeInTheDocument();
    expect(screen.getByText("+4.50%")).toBeInTheDocument();
  });

  it("shows an explicit rolling-return selection state when no window is supplied", async () => {
    installSuccessfulFetch();
    renderPage();

    expect(
      await screen.findByText("Choose a rolling window"),
    ).toBeInTheDocument();
  });

  it("shows the server diagnostic when the selected rolling window exceeds available history", async () => {
  const analytics = analyticsFixture();

  analytics.rolling_return_window = 100;
  analytics.rolling_returns = [];
  analytics.warnings = [
    {
      code: "INSUFFICIENT_ROLLING_HISTORY",
      message:
        "Rolling return requires at least 100 daily return observations.",
      observations: 42,
    },
  ];

  installSuccessfulFetch(analytics);

  renderPage(
    `/portfolios/${PORTFOLIO_ID}/analysis?range=6M&rollingWindow=100`,
  );

  const rollingHeading = await screen.findByRole("heading", {
    name: "Rolling returns",
  });

  const rollingSection = rollingHeading.closest("section");

  expect(rollingSection).not.toBeNull();

  expect(
    within(rollingSection!).getByText(
      "Rolling return unavailable",
    ),
  ).toBeInTheDocument();

  expect(
    within(rollingSection!).getByText(
      "Rolling return requires at least 100 daily return observations.",
    ),
  ).toBeInTheDocument();

  expect(
    screen.getByText("100-observation window"),
  ).toBeInTheDocument();
});

  it("renders undefined benchmark correlation with the server diagnostic", async () => {
    const analytics = analyticsFixture();

    analytics.benchmark_correlation = {
      value: null,
      observations: 40,
      warnings: [
        {
          code: "ZERO_BENCHMARK_VARIANCE",
          message:
            "Correlation is undefined because benchmark sample variance is zero.",
        },
      ],
    };

    analytics.warnings = [
      {
        code: "UNDEFINED_CORRELATION",
        message:
          "Correlation is undefined because benchmark sample variance is zero.",
        observations: 40,
      },
    ];

    installSuccessfulFetch(analytics);
    renderPage();

    const label = await screen.findByText("Benchmark correlation");
    const card = label.closest("article");

    expect(card).not.toBeNull();
    expect(
      within(card!).getByText("Not available"),
    ).toBeInTheDocument();
    expect(
      within(card!).getByText(
        "Correlation is undefined because benchmark sample variance is zero.",
      ),
    ).toBeInTheDocument();
  });

  it("renders provenance, assumptions, observations, and benchmark identity", async () => {
    installSuccessfulFetch();
    renderPage();

    expect(
      await screen.findByText("Calculation provenance"),
    ).toBeInTheDocument();
    expect(screen.getByText("mock")).toBeInTheDocument();
    expect(screen.getByText("adjusted_close")).toBeInTheDocument();
    expect(screen.getAllByText("SPY").length).toBeGreaterThan(0);
    expect(screen.getByText("0.1.0.dev0")).toBeInTheDocument();
    expect(
      screen.getByText("2026-08-01 to 2026-09-15"),
    ).toBeInTheDocument();
    expect(screen.getByText("252")).toBeInTheDocument();
    expect(
      screen.getByText("historical returns use adjusted_close"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("current allocation uses raw close"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "benchmark correlation uses Pearson correlation on exact date intersections",
      ),
    ).toBeInTheDocument();

    const portfolioObservations = screen
      .getByText("Portfolio observations")
      .closest("article");
    const benchmarkObservations = screen
      .getByText("Benchmark observations")
      .closest("article");

    expect(
      within(portfolioObservations!).getByText("42"),
    ).toBeInTheDocument();
    expect(
      within(benchmarkObservations!).getByText("40"),
    ).toBeInTheDocument();
  });

  it("preserves range context in the back link and accessible range controls", async () => {
    installSuccessfulFetch();

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
    );

    expect(await screen.findByText("Range 6M")).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Portfolio dashboard",
      }),
    ).toHaveAttribute(
      "href",
      `/portfolios/${PORTFOLIO_ID}/dashboard?range=6M`,
    );

    const periodControls = screen.getByRole("region", {
      name: "Analysis period controls",
    });

    const sixMonths = within(periodControls).getByRole("button", {
      name: "6M",
    });
    const oneYear = within(periodControls).getByRole("button", {
      name: "1Y",
    });

    expect(sixMonths).toHaveAttribute("aria-pressed", "true");
    expect(oneYear).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(oneYear);

    expect(oneYear).toHaveAttribute("aria-pressed", "true");
  });

  it("submits an explicit rolling window while preserving the selected range", async () => {
    const fetchMock = installSuccessfulFetch(analyticsFixtureWithRolling());

    renderPage(
      `/portfolios/${PORTFOLIO_ID}/analysis?range=6M`,
    );

    await screen.findByRole("heading", {
      name: "Analytical results",
    });

    fireEvent.change(
      screen.getByRole("spinbutton", {
        name: "Rolling window",
      }),
      {
        target: { value: "20" },
      },
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Apply window",
      }),
    );

    await screen.findByText("20-observation window");

    const analyticsUrls = fetchMock.mock.calls
      .map((call) => String(call[0]))
      .filter((url) =>
        url.includes(
          `/api/v1/analytics/portfolios/${PORTFOLIO_ID}/`,
        ),
      );

    expect(
      analyticsUrls.some((url) =>
        url.includes("rolling_window=20"),
      ),
    ).toBe(true);
  });

  it("shows a loading state while portfolio context is being retrieved", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>(() => undefined),
      ),
    );

    renderPage();

    expect(
      screen.getByLabelText("Loading portfolio analysis"),
    ).toBeInTheDocument();
  });

  it.each<[number, string, string, string]>([
    [
      403,
      "FORBIDDEN",
      "You do not have access to this portfolio.",
      "Portfolio access denied",
    ],
    [
      404,
      "PORTFOLIO_NOT_FOUND",
      "Portfolio was not found.",
      "Portfolio not found",
    ],
    [
      503,
      "PORTFOLIO_ANALYTICS_FAILED",
      "Analytics dependency failed.",
      "Portfolio analysis could not load",
    ],
  ])(
    "renders the expected %s analytics error state",
    async (status, code, detail, expectedTitle) => {
      installAnalyticsError(status, {
        code,
        detail,
      });

      renderPage();

      expect(
        await screen.findByText(expectedTitle),
      ).toBeInTheDocument();
    
      expect(screen.getByText(detail)).toBeInTheDocument();

      expect(
        screen.getByRole("button", {
          name: "Retry",
        }),
      ).toBeInTheDocument();
    },
  );
});
````

---

# File: `src/pages/PortfolioAnalysisPage.tsx`

````tsx
import { useMemo, type ReactNode } from "react";
import {
  Link,
  useParams,
  useSearchParams,
} from "react-router";

import { ApiError } from "../api/client";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  DASHBOARD_RANGES,
  resolveDashboardDateRange,
  type DashboardRange,
} from "../features/dashboard/dateRange";
import {
  formatDate,
  formatPercent,
  humanizeCode,
} from "../features/dashboard/formatting";
import {
  usePortfolioAnalytics,
  usePortfolios,
} from "../hooks/usePortfolioData";
import { DashboardShell } from "../layouts/DashboardShell";
import type {
  EngineWarning,
  PortfolioAnalyticsResult,
  PortfolioAnalyticsWarningCode,
} from "../types/analytics";

function isDashboardRange(
  value: string | null,
): value is DashboardRange {
  return (
    value !== null &&
    DASHBOARD_RANGES.includes(value as DashboardRange)
  );
}

function formatUnsignedPercent(
  value: number | null,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatRatio(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatIndex(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  }).format(value);
}

function formatCount(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCurrencyNumber(
  value: number | null,
  currency: string,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function warningMessagesFor(
  analytics: PortfolioAnalyticsResult,
  codes: readonly PortfolioAnalyticsWarningCode[],
): string[] {
  const codeSet = new Set<PortfolioAnalyticsWarningCode>(codes);

  return analytics.warnings
    .filter((warning) => codeSet.has(warning.code))
    .map((warning) => warning.message);
}

function engineWarningMessages(
  warnings: EngineWarning[] | undefined,
): string[] {
  return warnings?.map((warning) => warning.message) ?? [];
}

function uniqueMessages(
  ...groups: readonly string[][]
): string[] {
  return Array.from(new Set(groups.flat()));
}

interface AnalysisMetricCardProps {
  label: string;
  value: string;
  description: string;
  diagnostics?: string[];
  footer?: ReactNode;
}

function AnalysisMetricCard({
  label,
  value,
  description,
  diagnostics = [],
  footer,
}: AnalysisMetricCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold tabular-nums tracking-tight text-slate-950">
        {value}
      </p>

      <p className="mt-2 text-xs leading-5 text-slate-500">
        {description}
      </p>

      {diagnostics.length > 0 ? (
        <ul className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-xs leading-5 text-amber-900">
          {diagnostics.map((diagnostic) => (
            <li key={diagnostic}>{diagnostic}</li>
          ))}
        </ul>
      ) : null}

      {footer ? (
        <div className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">
          {footer}
        </div>
      ) : null}
    </article>
  );
}

function AnalysisSkeleton() {
  return (
    <div aria-label="Loading portfolio analysis">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-3 h-8 w-64" />
        <Skeleton className="mt-4 h-5 w-full max-w-2xl" />
      </section>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton
            key={index}
            className="h-40 w-full rounded-2xl"
          />
        ))}
      </div>
    </div>
  );
}

function AnalysisWarnings({
  analytics,
}: {
  analytics: PortfolioAnalyticsResult;
}) {
  if (analytics.warnings.length === 0) {
    return null;
  }

  return (
    <section
      className="mt-5 rounded-3xl border border-amber-200 bg-amber-50 p-5 sm:p-6"
      aria-labelledby="analysis-warnings-heading"
    >
      <h2
        id="analysis-warnings-heading"
        className="text-lg font-semibold tracking-tight text-amber-950"
      >
        Analytical warnings
      </h2>

      <p className="mt-1 text-sm leading-6 text-amber-900">
        These diagnostics come from the server calculation and explain
        unavailable or limited results.
      </p>

      <ul className="mt-4 space-y-3">
        {analytics.warnings.map((warning, index) => (
          <li
            key={`${warning.code}-${warning.observations ?? "none"}-${index}`}
            className="rounded-2xl border border-amber-200 bg-white/70 px-4 py-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-amber-200 bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-950">
                {humanizeCode(warning.code)}
              </span>

              {warning.observations !== null ? (
                <span className="text-xs text-amber-800">
                  {warning.observations} observations
                </span>
              ) : null}
            </div>

            <p className="mt-2 text-sm leading-6 text-amber-950">
              {warning.message}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AnalysisContent({
  analytics,
  currency,
}: {
  analytics: PortfolioAnalyticsResult;
  currency: string;
}) {
  const performanceUnavailable = warningMessagesFor(analytics, [
    "PERFORMANCE_UNAVAILABLE",
  ]);

  const insufficientHistory = warningMessagesFor(analytics, [
    "INSUFFICIENT_HISTORY",
  ]);

  const cagrWarnings = warningMessagesFor(analytics, [
    "PERFORMANCE_UNAVAILABLE",
    "UNDEFINED_CAGR",
  ]);

  const sharpeWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "INSUFFICIENT_HISTORY",
      "UNDEFINED_SHARPE",
    ]),
    engineWarningMessages(analytics.sharpe?.warnings),
  );

  const sortinoWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "INSUFFICIENT_HISTORY",
      "UNDEFINED_SORTINO",
    ]),
    engineWarningMessages(analytics.sortino?.warnings),
  );

  const drawdownWarnings = uniqueMessages(
    performanceUnavailable,
    engineWarningMessages(analytics.maximum_drawdown?.warnings),
  );

  const betaWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "BENCHMARK_NOT_CONFIGURED",
      "BENCHMARK_NOT_FOUND",
      "BENCHMARK_NO_DATA",
      "BENCHMARK_PROVIDER_FAILED",
      "UNDEFINED_BETA",
    ]),
    engineWarningMessages(analytics.beta?.warnings),
  );

  const correlationWarnings = uniqueMessages(
    warningMessagesFor(analytics, [
      "PERFORMANCE_UNAVAILABLE",
      "BENCHMARK_NOT_CONFIGURED",
      "BENCHMARK_NOT_FOUND",
      "BENCHMARK_NO_DATA",
      "BENCHMARK_PROVIDER_FAILED",
      "UNDEFINED_CORRELATION",
    ]),
    engineWarningMessages(analytics.benchmark_correlation?.warnings),
  );

  const rollingWarnings = warningMessagesFor(analytics, [
    "INSUFFICIENT_ROLLING_HISTORY",
  ]);

  const allocationWarnings = warningMessagesFor(analytics, [
    "CURRENT_VALUATION_INCOMPLETE",
    "CURRENT_ALLOCATION_UNAVAILABLE",
  ]);

  const limitedHistory = analytics.warnings.some(
    (warning) => warning.code === "INSUFFICIENT_HISTORY",
  );

  const partialValuation = analytics.warnings.some(
    (warning) => warning.code === "CURRENT_VALUATION_INCOMPLETE",
  );

  const sourceWarnings = analytics.warnings.some(
    (warning) => warning.code === "SOURCE_WARNING",
  );

  return (
    <>
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
              Deterministic analytics
            </p>

            <h2 className="mt-1 text-xl font-semibold tracking-tight text-slate-950">
              Analytical results
            </h2>

            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              All financial values below are supplied by the backend analytics
              contract. The frontend formats values and exposes diagnostics
              without recalculating portfolio metrics.
            </p>
          </div>

          <div
            className="flex flex-wrap gap-2"
            aria-label="Analysis status"
          >
            {limitedHistory ? (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
                Limited history
              </span>
            ) : null}

            {partialValuation ? (
              <span className="rounded-full border border-orange-200 bg-orange-50 px-2.5 py-1 text-xs font-semibold text-orange-900">
                Partial current valuation
              </span>
            ) : null}

            {sourceWarnings ? (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
                Source warnings
              </span>
            ) : null}

            {!limitedHistory && !partialValuation && !sourceWarnings ? (
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                Analysis available
              </span>
            ) : null}
          </div>
        </div>
      </section>

      <section
        className="mt-5"
        aria-labelledby="return-risk-heading"
      >
        <div className="mb-3">
          <h2
            id="return-risk-heading"
            className="text-lg font-semibold text-slate-950"
          >
            Return and risk
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Historical results for the server-provided effective analytical
            period.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <AnalysisMetricCard
            label="Cumulative return"
            value={formatPercent(analytics.cumulative_return)}
            description="Time-weighted cumulative portfolio return."
            diagnostics={performanceUnavailable}
          />

          <AnalysisMetricCard
            label="CAGR"
            value={formatPercent(analytics.cagr?.value ?? null)}
            description="Annualized geometric return using the server's elapsed-period convention."
            diagnostics={cagrWarnings}
            footer={
              analytics.cagr ? (
                <>
                  {analytics.cagr.elapsed_days} elapsed days
                  {analytics.cagr.is_short_period
                    ? " · Annualized short period"
                    : ""}
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Annualized volatility"
            value={formatUnsignedPercent(analytics.annualized_volatility)}
            description="Annualized sample volatility of daily portfolio returns."
            diagnostics={uniqueMessages(
              insufficientHistory,
              performanceUnavailable,
            )}
          />

          <AnalysisMetricCard
            label="Maximum drawdown"
            value={formatPercent(
              analytics.maximum_drawdown?.value ?? null,
            )}
            description="Largest peak-to-trough wealth decline in the analyzed return series."
            diagnostics={drawdownWarnings}
            footer={
              analytics.maximum_drawdown ? (
                <>
                  {analytics.maximum_drawdown.observations} return observations
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Sharpe ratio"
            value={formatRatio(analytics.sharpe?.value ?? null)}
            description="Annualized excess-return ratio using the backend risk-free-rate assumption."
            diagnostics={sharpeWarnings}
            footer={
              analytics.sharpe ? (
                <>
                  Risk-free rate{" "}
                  {formatUnsignedPercent(
                    analytics.sharpe.risk_free_rate_annual,
                  )}
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Sortino ratio"
            value={formatRatio(analytics.sortino?.value ?? null)}
            description="Annualized downside-risk ratio using the backend minimum acceptable return."
            diagnostics={sortinoWarnings}
            footer={
              analytics.sortino ? (
                <>
                  Minimum acceptable return{" "}
                  {formatUnsignedPercent(
                    analytics.sortino.minimum_acceptable_return_annual,
                  )}
                </>
              ) : null
            }
          />

          <AnalysisMetricCard
            label="Downside deviation"
            value={formatUnsignedPercent(
              analytics.sortino?.downside_deviation ?? null,
            )}
            description="Downside deviation returned with the canonical Sortino calculation."
            diagnostics={sortinoWarnings}
          />

          <AnalysisMetricCard
            label="Beta"
            value={formatRatio(analytics.beta?.value ?? null)}
            description="Portfolio beta against the configured benchmark using aligned observations."
            diagnostics={betaWarnings}
            footer={
              analytics.provenance.benchmark ? (
                <>Benchmark {analytics.provenance.benchmark}</>
              ) : (
                <>No configured benchmark</>
              )
            }
          />

          <AnalysisMetricCard
            label="Benchmark correlation"
            value={formatRatio(
              analytics.benchmark_correlation?.value ?? null,
            )}
            description="Pearson correlation against the configured benchmark using exact-date-aligned daily returns."
            diagnostics={correlationWarnings}
            footer={
              analytics.benchmark_correlation ? (
                <>
                  {analytics.benchmark_correlation.observations} aligned
                  observations
                </>
              ) : analytics.provenance.benchmark ? (
                <>Benchmark {analytics.provenance.benchmark}</>
              ) : (
                <>No configured benchmark</>
              )
            }
          />

          <AnalysisMetricCard
            label="Portfolio observations"
            value={formatCount(analytics.observations)}
            description="Daily portfolio return observations used by the analytical service."
          />

          <AnalysisMetricCard
            label="Benchmark observations"
            value={formatCount(analytics.benchmark_observations)}
            description="Benchmark return observations available for aligned benchmark analytics."
            diagnostics={uniqueMessages(betaWarnings, correlationWarnings)}
          />
        </div>
      </section>

      <section
        className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="rolling-return-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2
              id="rolling-return-heading"
              className="text-lg font-semibold tracking-tight text-slate-950"
            >
              Rolling returns
            </h2>

            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Trailing cumulative return over an explicit number of daily return
              observations. No rolling window is assumed by the frontend or
              backend.
            </p>
          </div>

          {analytics.rolling_return_window !== null ? (
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700">
              {analytics.rolling_return_window}-observation window
            </span>
          ) : null}
        </div>

        {analytics.rolling_return_window === null ? (
          <div className="mt-4">
            <StatePanel
              title="Choose a rolling window"
              message="Enter a positive number of daily return observations above to request a server-calculated rolling-return series."
            />
          </div>
        ) : analytics.rolling_returns.length === 0 ? (
          <div className="mt-4">
            <StatePanel
              title="Rolling return unavailable"
              message={
                rollingWarnings[0] ??
                "The selected period does not contain enough return observations for this rolling window."
              }
            />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[28rem] border-separate border-spacing-0 text-left text-sm">
              <caption className="sr-only">
                Server-calculated rolling cumulative returns
              </caption>

              <thead>
                <tr className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                  <th
                    scope="col"
                    className="border-b border-slate-200 px-3 py-2"
                  >
                    Period end
                  </th>
                  <th
                    scope="col"
                    className="border-b border-slate-200 px-3 py-2 text-right"
                  >
                    Rolling return
                  </th>
                </tr>
              </thead>

              <tbody>
                {analytics.rolling_returns.map((observation) => (
                  <tr key={observation.period_end}>
                    <td className="border-b border-slate-100 px-3 py-3 text-slate-700">
                      {formatDate(observation.period_end)}
                    </td>

                    <td className="border-b border-slate-100 px-3 py-3 text-right font-semibold tabular-nums text-slate-950">
                      {formatPercent(observation.value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section
        className="mt-5 grid gap-5 xl:grid-cols-2"
        aria-label="Current allocation and concentration"
      >
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            Current allocation context
          </h2>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            Current allocation uses the server's raw-close valuation boundary
            and is separate from historical adjusted-close return analytics.
          </p>

          {analytics.current_allocation === null ? (
            <div className="mt-4">
              <StatePanel
                title="Current allocation unavailable"
                message={
                  allocationWarnings[0] ??
                  "The analytics response did not include a current allocation result."
                }
              />
            </div>
          ) : (
            <dl className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Market value
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatCurrencyNumber(
                    analytics.current_allocation.total_market_value,
                    currency,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Cash weight
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatUnsignedPercent(
                    analytics.current_allocation.cash_weight,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Security positions
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {analytics.current_allocation.positions.length}
                </dd>
              </div>
            </dl>
          )}
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            Concentration
          </h2>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            Concentration measures come directly from the current normalized
            portfolio weights.
          </p>

          {analytics.concentration === null ? (
            <div className="mt-4">
              <StatePanel
                title="Concentration unavailable"
                message={
                  allocationWarnings[0] ??
                  "The analytics response did not include concentration measures."
                }
              />
            </div>
          ) : (
            <dl className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Largest position
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatUnsignedPercent(
                    analytics.concentration.largest_position_weight,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  {analytics.concentration.hhi_includes_cash
                    ? "HHI (includes cash)"
                    : "Security-only HHI"}
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {formatIndex(
                    analytics.concentration.herfindahl_hirschman_index,
                  )}
                </dd>
              </div>

              <div className="rounded-2xl bg-slate-50 p-4">
                <dt className="text-xs font-medium text-slate-500">
                  Security count
                </dt>
                <dd className="mt-1 font-semibold tabular-nums text-slate-950">
                  {analytics.concentration.security_position_count}
                </dd>
              </div>
            </dl>
          )}
        </div>
      </section>

      <AnalysisWarnings analytics={analytics} />

      <section
        className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
        aria-labelledby="analysis-provenance-heading"
      >
        <h2
          id="analysis-provenance-heading"
          className="text-lg font-semibold tracking-tight text-slate-950"
        >
          Calculation provenance
        </h2>

        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <dt className="text-xs font-medium text-slate-500">
              As of
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {formatDate(analytics.provenance.as_of_date)}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Effective period
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.period_start} to{" "}
              {analytics.provenance.period_end}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Provider
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.data_source}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Price field
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.price_field}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Benchmark
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.benchmark ?? "Not available"}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Annualization factor
            </dt>
            <dd className="mt-1 font-medium tabular-nums text-slate-900">
              {formatCount(analytics.provenance.annualization_factor)}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Engine version
            </dt>
            <dd className="mt-1 font-medium text-slate-900">
              {analytics.provenance.engine_version}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium text-slate-500">
              Provenance warnings
            </dt>
            <dd className="mt-1 font-medium tabular-nums text-slate-900">
              {analytics.provenance.warnings.length}
            </dd>
          </div>
        </dl>

        <div className="mt-5 border-t border-slate-100 pt-4">
          <h3 className="text-sm font-semibold text-slate-900">
            Assumptions
          </h3>

          <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-600">
            {analytics.provenance.assumptions.map((assumption) => (
              <li key={assumption}>{assumption}</li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}

export function PortfolioAnalysisPage() {
  const { portfolioId } = useParams<{
    portfolioId: string;
  }>();

  const [searchParams, setSearchParams] = useSearchParams();
  const portfoliosQuery = usePortfolios();

  const selectedPortfolio = portfoliosQuery.data?.find(
    (portfolio) => portfolio.id === portfolioId,
  );

  const rangeParam = searchParams.get("range");

  const range: DashboardRange = isDashboardRange(rangeParam)
    ? rangeParam
    : "1M";

  const rollingWindowParam = searchParams.get("rollingWindow");

  const parsedRollingWindow =
    rollingWindowParam === null ? undefined : Number(rollingWindowParam);

  const rollingWindow =
    parsedRollingWindow !== undefined &&
    Number.isInteger(parsedRollingWindow) &&
    parsedRollingWindow > 0
      ? parsedRollingWindow
      : undefined;

  const request = useMemo(() => {
    if (!portfolioId || !selectedPortfolio) {
      return null;
    }

    const dates = resolveDashboardDateRange(
      range,
      selectedPortfolio.created_at,
    );

    return {
      portfolioId,
      start: dates.start,
      end: dates.end,
      rollingWindow,
    };
  }, [
    portfolioId,
    range,
    rollingWindow,
    selectedPortfolio,
  ]);

  const analyticsQuery = usePortfolioAnalytics(request);
  const analytics = analyticsQuery.data;

  const backPath = portfolioId
    ? `/portfolios/${encodeURIComponent(
        portfolioId,
      )}/dashboard?range=${encodeURIComponent(range)}`
    : "/";

  const error =
    analyticsQuery.error instanceof Error
      ? analyticsQuery.error
      : portfoliosQuery.error instanceof Error
        ? portfoliosQuery.error
        : null;

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
          <Link
            to={backPath}
            className="outline-none hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Portfolio dashboard
          </Link>

          <span aria-hidden="true">/</span>
          <span>Portfolio analysis</span>
        </div>

        <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          {selectedPortfolio?.name ?? "Portfolio analysis"}
        </h1>
      </div>

      <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
        Range {range === "ALL" ? "All" : range}
      </span>
    </div>
  );

  return (
    <DashboardShell header={header}>
      <section
        className="mb-5 flex flex-wrap items-end justify-between gap-4"
        aria-label="Analysis period controls"
      >
        <div>
          <p className="text-sm font-medium text-slate-500">
            Requested period
          </p>

          <p className="mt-0.5 text-sm text-slate-700">
            {request
              ? `${request.start} to ${request.end} (end exclusive)`
              : "Waiting for portfolio context"}
          </p>
        </div>

        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();

            const form = new FormData(event.currentTarget);
            const rawValue = String(
              form.get("rollingWindow") ?? "",
            ).trim();

            const next = new URLSearchParams(searchParams);

            if (!rawValue) {
              next.delete("rollingWindow");
              setSearchParams(next);
              return;
            }

            const value = Number(rawValue);

            if (!Number.isInteger(value) || value <= 0) {
              return;
            }

            next.set("rollingWindow", String(value));
            setSearchParams(next);
          }}
        >
          <label className="block text-xs font-medium text-slate-600">
            Rolling window
            <input
              key={rollingWindowParam ?? "none"}
              name="rollingWindow"
              type="number"
              min={1}
              step={1}
              defaultValue={rollingWindowParam ?? ""}
              placeholder="e.g. 21"
              className="mt-1 block w-32 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </label>

          <button
            type="submit"
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none transition hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
          >
            Apply window
          </button>
        </form>

        <div className="flex flex-wrap gap-1 rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
          {DASHBOARD_RANGES.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={range === option}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                next.set("range", option);
                setSearchParams(next);
              }}
              className={`rounded-xl px-3 py-2 text-xs font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 ${
                range === option
                  ? "bg-slate-950 text-white"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              {option === "ALL" ? "All" : option}
            </button>
          ))}
        </div>
      </section>

      {!portfoliosQuery.isPending &&
      portfoliosQuery.data &&
      !selectedPortfolio ? (
        <StatePanel
          title="Portfolio not found"
          message="This portfolio is not available in the authenticated account scope."
          tone="error"
          action={
            <Link
              to="/"
              className="inline-flex rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Choose a portfolio
            </Link>
          }
        />
      ) : portfoliosQuery.isPending ||
        (analyticsQuery.isPending && analytics === undefined) ? (
        <AnalysisSkeleton />
      ) : error !== null && analytics === undefined ? (
        <StatePanel
          title={
            error instanceof ApiError && error.status === 403
              ? "Portfolio access denied"
              : error instanceof ApiError && error.status === 404
                ? "Portfolio not found"
                : error instanceof ApiError &&
                    error.status === 400 &&
                    error.code === "INSUFFICIENT_ANALYTICS_PERIOD"
                  ? "Analysis period is insufficient"
                  : "Portfolio analysis could not load"
          }
          message={error.message}
          tone="error"
          action={
            <button
              type="button"
              onClick={() => {
                void portfoliosQuery.refetch();

                if (request !== null) {
                  void analyticsQuery.refetch();
                }
              }}
              className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Retry
            </button>
          }
        />
      ) : analytics === undefined ? (
        <StatePanel
          title="No portfolio analysis"
          message="No analytical result is available for this portfolio and selected period."
        />
      ) : (
        <div className="relative">
          {error !== null ? (
            <div
              className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
              role="status"
            >
              Refresh failed. Showing the most recent successful analytical
              result.
            </div>
          ) : null}

          {analyticsQuery.isFetching ? (
            <div
              className="mb-4 inline-flex rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800"
              role="status"
              aria-live="polite"
            >
              Refreshing analysis…
            </div>
          ) : null}

          <AnalysisContent
            analytics={analytics}
            currency={selectedPortfolio?.base_currency ?? "USD"}
          />
        </div>
      )}
    </DashboardShell>
  );
}
````

---

# File: `src/test/setup.ts`

````typescript
import "@testing-library/jest-dom/vitest";
````

---

# File: `src/types/analytics.ts`

````typescript
export interface EngineWarning {
  code: string;
  message: string;
}

export interface AnnualizedReturnResult {
  value: number;
  wealth_ratio: number;
  elapsed_days: number;
  elapsed_years: number;
  is_short_period: boolean;
}

export interface SharpeRatioResult {
  value: number | null;
  observations: number;
  risk_free_rate_annual: number;
  risk_free_rate_daily: number;
  annualization_factor: number;
  warnings: EngineWarning[];
}

export interface SortinoRatioResult {
  value: number | null;
  observations: number;
  minimum_acceptable_return_annual: number;
  minimum_acceptable_return_daily: number;
  downside_deviation: number | null;
  annualization_factor: number;
  warnings: EngineWarning[];
}

export interface MaximumDrawdownResult {
  value: number | null;
  observations: number;
  peak_index: number | null;
  trough_index: number | null;
  warnings: EngineWarning[];
}

export interface BetaResult {
  value: number | null;
  observations: number;
  warnings: EngineWarning[];
}

export interface CorrelationResult {
  value: number | null;
  observations: number;
  warnings: EngineWarning[];
}

export interface RollingReturnObservation {
  period_end: string;
  value: number;
}

export interface SecurityAllocation {
  asset_id: string;
  market_value: number;
  weight: number;
}

export interface PortfolioAllocationResult {
  positions: SecurityAllocation[];
  cash_value: number;
  cash_weight: number;
  total_market_value: number;
  weight_sum: number;
  weight_sum_tolerance: number;
}

export interface ConcentrationResult {
  largest_position_weight: number | null;
  herfindahl_hirschman_index: number;
  security_position_count: number;
  cash_weight: number;
  largest_position_includes_cash: boolean;
  hhi_includes_cash: boolean;
  long_only: boolean;
  weight_sum_tolerance: number;
}

export interface AnalyticalResultProvenance {
  engine_version: string;
  as_of_date: string;
  period_start: string;
  period_end: string;
  data_source: string;
  price_field: string;
  annualization_factor: number;
  benchmark: string | null;
  assumptions: string[];
  warnings: string[];
}

export type PortfolioAnalyticsWarningCode =
  | "SOURCE_WARNING"
  | "PERFORMANCE_UNAVAILABLE"
  | "INSUFFICIENT_HISTORY"
  | "INSUFFICIENT_ROLLING_HISTORY"
  | "UNDEFINED_CAGR"
  | "UNDEFINED_SHARPE"
  | "UNDEFINED_SORTINO"
  | "BENCHMARK_NOT_CONFIGURED"
  | "BENCHMARK_NOT_FOUND"
  | "BENCHMARK_NO_DATA"
  | "BENCHMARK_PROVIDER_FAILED"
  | "UNDEFINED_BETA"
  | "UNDEFINED_CORRELATION"
  | "CURRENT_VALUATION_INCOMPLETE"
  | "CURRENT_ALLOCATION_UNAVAILABLE";

export interface PortfolioAnalyticsWarning {
  code: PortfolioAnalyticsWarningCode;
  message: string;
  observations: number | null;
}

export interface PortfolioAnalyticsResult {
  portfolio_id: string;
  observations: number;
  benchmark_observations: number | null;
  cumulative_return: number | null;
  cagr: AnnualizedReturnResult | null;
  annualized_volatility: number | null;
  sharpe: SharpeRatioResult | null;
  sortino: SortinoRatioResult | null;
  maximum_drawdown: MaximumDrawdownResult | null;
  beta: BetaResult | null;
  benchmark_correlation: CorrelationResult | null;
  current_allocation: PortfolioAllocationResult | null;
  concentration: ConcentrationResult | null;
  rolling_return_window: number | null;
  rolling_returns: RollingReturnObservation[];
  provenance: AnalyticalResultProvenance;
  warnings: PortfolioAnalyticsWarning[];
}
````

---

# File: `src/types/dashboard.ts`

````typescript
import type { PortfolioAnalyticsResult } from "./analytics";

export type PerformanceDataQuality =
  | "CURRENT"
  | "STALE"
  | "PARTIAL"
  | "UNAVAILABLE";

export type DashboardSnapshotModule =
  | "SUMMARY"
  | "PERFORMANCE"
  | "ALLOCATION"
  | "HOLDINGS"
  | "MOVERS"
  | "ANALYTICS"
  | "REVIEW_ITEMS";

export type DashboardSnapshotModuleStatus = "AVAILABLE" | "UNAVAILABLE";

export interface PortfolioListItem {
  id: string;
  name: string;
  base_currency: string;
  benchmark_asset_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardSnapshotModuleState {
  module: DashboardSnapshotModule;
  status: DashboardSnapshotModuleStatus;
  error_code: string | null;
  detail: string | null;
}

export interface DashboardSnapshotContext {
  snapshot_id: string;
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  valuation_cutoff: string;
  calculated_at: string;
  engine_version: string;
  current_data_as_of: string | null;
  historical_data_as_of: string | null;
  analytics_as_of_date: string | null;
}

export interface PortfolioPerformanceSummary {
  starting_value: string | null;
  ending_value: string | null;
  value_change: string | null;
  net_external_flow: string;
  investment_gain_loss: string | null;
  cumulative_return: number | null;
  benchmark_cumulative_return: number | null;
}

export interface PortfolioPerformancePoint {
  observation_date: string;
  portfolio_value: string | null;
  net_external_flow: string;
  daily_return: number | null;
  cumulative_return: number | null;
  data_quality: PerformanceDataQuality;
  warnings: string[];
}

export interface BenchmarkPerformancePoint {
  observation_date: string;
  adjusted_close: string | null;
  cumulative_return: number | null;
  data_quality: PerformanceDataQuality;
}

export interface DashboardPerformanceWarning {
  code: string;
  message: string;
  observation_date: string | null;
  asset_id: string | null;
  symbol: string | null;
}

export interface DashboardPerformanceProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  data_as_of: string | null;
  calculated_at: string;
  engine_version: string;
  price_field: string;
  benchmark_asset_id: string | null;
  benchmark_symbol: string | null;
}

export interface DashboardPerformanceResult {
  summary: PortfolioPerformanceSummary;
  points: PortfolioPerformancePoint[];
  benchmark_points: BenchmarkPerformancePoint[];
  portfolio_data_quality: PerformanceDataQuality;
  benchmark_data_quality: PerformanceDataQuality | null;
  warnings: DashboardPerformanceWarning[];
  provenance: DashboardPerformanceProvenance;
}

export type PortfolioSummaryUnavailableReason =
  | "CURRENT_VALUATION_INCOMPLETE"
  | "TOTAL_MARKET_VALUE_NON_POSITIVE"
  | "SELECTED_PERIOD_NOT_STARTED";

export interface DashboardPortfolioSummaryMetrics {
  total_market_value: string | null;
  total_market_value_unavailable_reason: PortfolioSummaryUnavailableReason | null;
  net_contributions: string;
  cost_basis: string;
  cash_balance: string;
  cash_percentage: string | null;
  cash_percentage_unavailable_reason: PortfolioSummaryUnavailableReason | null;
  unrealized_gain_loss: string | null;
  unrealized_gain_loss_unavailable_reason: PortfolioSummaryUnavailableReason | null;
  selected_period_realized_gain_loss: string | null;
  selected_period_realized_gain_loss_unavailable_reason:
    | PortfolioSummaryUnavailableReason
    | null;
  selected_period_income_received: string | null;
  selected_period_income_unavailable_reason: PortfolioSummaryUnavailableReason | null;
}

export interface DashboardPortfolioSummaryProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  ledger_as_of: string;
  current_price_data_as_of: string | null;
  calculated_at: string;
  current_price_field: string;
  accounting_method: string;
  accounting_assumptions: string[];
  selected_period_transaction_timezone: string;
  net_contributions_scope: string;
  selected_period_accounting_scope: string;
}

export interface DashboardPortfolioSummaryResult {
  metrics: DashboardPortfolioSummaryMetrics;
  data_quality: PerformanceDataQuality;
  warnings: string[];
  provenance: DashboardPortfolioSummaryProvenance;
}

export type DashboardAllocationUnavailableReason =
  | "CURRENT_VALUATION_INCOMPLETE"
  | "CURRENT_ALLOCATION_UNAVAILABLE";

export interface DashboardAllocationGroup {
  key: string;
  label: string;
  is_cash: boolean;
  asset_count: number;
  market_value: string;
  weight: number | null;
}

export interface DashboardAllocationTotals {
  total_market_value: string | null;
  invested_value: string | null;
  cash_value: string;
  invested_weight: number | null;
  cash_weight: number | null;
}

export interface DashboardAllocationProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  as_of: string;
  data_as_of: string | null;
  calculated_at: string;
  price_field: string;
  grouping_dimension: string;
  supported_grouping_dimensions: string[];
  grouping_source: string;
  ordering_rule: string;
  other_grouping_applied: boolean;
  other_grouping_threshold: number | null;
  other_grouping_rule: string;
  weight_sum_tolerance: number;
}

export interface DashboardAllocationResult {
  allocation_available: boolean;
  groups: DashboardAllocationGroup[];
  totals: DashboardAllocationTotals;
  data_quality: PerformanceDataQuality;
  unavailable_reason: DashboardAllocationUnavailableReason | null;
  warnings: string[];
  provenance: DashboardAllocationProvenance;
}

export interface AllocationGroupSelection {
  grouping_dimension: string;
  group_key: string;
}

export type HoldingMetricUnavailableReason =
  | "CURRENT_PRICE_UNAVAILABLE"
  | "PERIOD_HISTORY_UNAVAILABLE"
  | "PERIOD_START_PRICE_UNAVAILABLE"
  | "PERIOD_END_PRICE_UNAVAILABLE"
  | "CURRENT_ALLOCATION_UNAVAILABLE"
  | "CONTRIBUTION_NOT_CALCULATED";

export interface HoldingSparklinePoint {
  observation_date: string;
  adjusted_close: string | null;
}

export interface DashboardHoldingWarning {
  code: string;
  message: string;
  asset_id: string;
  symbol: string;
  observation_date: string | null;
}

export interface DashboardHolding {
  asset_id: string;
  symbol: string;
  name: string;
  asset_type: string;
  currency: string;
  quantity: string;
  current_price: string | null;
  current_price_date: string | null;
  current_price_retrieved_at: string | null;
  stale_trading_sessions: number | null;
  market_value: string | null;
  weight: number | null;
  weight_unavailable_reason: HoldingMetricUnavailableReason | null;
  selected_period_return: number | null;
  selected_period_return_unavailable_reason: HoldingMetricUnavailableReason | null;
  contribution_to_return: number | null;
  contribution_unavailable_reason: HoldingMetricUnavailableReason | null;
  sparkline: HoldingSparklinePoint[];
  data_quality: PerformanceDataQuality;
  warnings: DashboardHoldingWarning[];
}

export interface DashboardHoldingsProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  current_price_as_of: string | null;
  period_data_as_of: string | null;
  calculated_at: string;
  current_price_field: string;
  period_price_field: string;
}

export interface DashboardHoldingsResult {
  holdings: DashboardHolding[];
  data_quality: PerformanceDataQuality;
  warnings: DashboardHoldingWarning[];
  provenance: DashboardHoldingsProvenance;
}

export type MoversAttributionStatus = "AVAILABLE" | "UNAVAILABLE";

export type MoversAttributionUnavailableReason =
  | "PORTFOLIO_TWR_UNAVAILABLE";

export type MoverUnavailableReason =
  | "NOT_CURRENT_HOLDING"
  | "SELECTED_PERIOD_RETURN_UNAVAILABLE"
  | "CONTRIBUTION_UNAVAILABLE";

export interface DashboardMover {
  asset_id: string;
  symbol: string;
  name: string;
  asset_type: string;
  currency: string;
  is_current_holding: boolean;
  quantity: string | null;
  current_price: string | null;
  current_price_date: string | null;
  current_price_retrieved_at: string | null;
  stale_trading_sessions: number | null;
  market_value: string | null;
  weight: number | null;
  selected_period_return: number | null;
  contribution_to_return: number | null;
  sparkline: HoldingSparklinePoint[];
  data_quality: PerformanceDataQuality;
  unavailable_reasons: MoverUnavailableReason[];
}

export interface MoversReconciliation {
  status: MoversAttributionStatus;
  periods: number;
  cumulative_return: number | null;
  asset_contribution_total: number | null;
  unattributed_contribution: number | null;
  reconciliation_error: number | null;
  unavailable_reason: MoversAttributionUnavailableReason | null;
}

export interface DashboardMoversProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  current_price_as_of: string | null;
  period_data_as_of: string | null;
  calculated_at: string;
  current_price_field: string;
  period_price_field: string;
  attribution_method: string;
  engine_version: string;
}

export interface DashboardMoversResult {
  top_gainers: DashboardMover[];
  top_losers: DashboardMover[];
  largest_contributors: DashboardMover[];
  largest_detractors: DashboardMover[];
  reconciliation: MoversReconciliation;
  data_quality: PerformanceDataQuality;
  warnings: string[];
  provenance: DashboardMoversProvenance;
}

export interface DashboardSnapshotResult {
  snapshot: DashboardSnapshotContext;
  is_complete: boolean;
  modules: DashboardSnapshotModuleState[];
  summary: DashboardPortfolioSummaryResult | null;
  performance: DashboardPerformanceResult | null;
  allocation: DashboardAllocationResult | null;
  holdings: DashboardHoldingsResult | null;
  movers: DashboardMoversResult | null;
  analytics: PortfolioAnalyticsResult | null;
  review_items: DashboardReviewItemsResult | null;
}

export type ReviewItemSeverity = "ERROR" | "WARNING" | "INFO";

export type ReviewItemCategory =
  | "MARKET_DATA"
  | "DATA_COVERAGE"
  | "PROVIDER"
  | "VALUATION"
  | "ANALYTICS";

export type ReviewItemSource =
  | "CURRENT_VALUATION"
  | "DAILY_PERFORMANCE"
  | "ANALYTICS";

export type ReviewDrilldownResource =
  | "HOLDINGS"
  | "PERFORMANCE"
  | "ANALYTICS";

export interface DashboardReviewDrilldown {
  resource: ReviewDrilldownResource;
  portfolio_id: string;
  requested_start: string;
  requested_end_exclusive: string;
  asset_id: string | null;
  symbol: string | null;
  observation_date: string | null;
}

export interface DashboardReviewItem {
  key: string;
  source: ReviewItemSource;
  severity: ReviewItemSeverity;
  category: ReviewItemCategory;
  code: string;
  message: string;
  drilldown: DashboardReviewDrilldown;
}

export interface DashboardReviewCount<TKey extends string = string> {
  key: TKey;
  count: number;
}

export interface DashboardReviewCounts {
  total: number;
  by_severity: DashboardReviewCount<ReviewItemSeverity>[];
  by_category: DashboardReviewCount<ReviewItemCategory>[];
}

export interface DashboardReviewFilters {
  severity: ReviewItemSeverity | null;
  category: ReviewItemCategory | null;
}

export interface DashboardReviewProvenance {
  portfolio_id: string;
  base_currency: string;
  provider: string;
  requested_start: string;
  requested_end_exclusive: string;
  effective_start: string;
  effective_end_exclusive: string;
  current_data_as_of: string | null;
  historical_data_as_of: string | null;
  analytics_as_of_date: string;
  calculated_at: string;
  engine_version: string;
  included_sources: ReviewItemSource[];
  ordering_rule: string;
}

export interface DashboardReviewItemsResult {
  counts: DashboardReviewCounts;
  filtered_count: number;
  filters: DashboardReviewFilters;
  items: DashboardReviewItem[];
  provenance: DashboardReviewProvenance;
}
````

---

# File: `tsconfig.json`

````json
{
  "compilerOptions": {
    "target": "ES2023",
    "useDefineForClassFields": true,
    "lib": [
      "ES2023",
      "DOM",
      "DOM.Iterable"
    ],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "types": [
      "node",
      "vite/client",
      "vitest/globals",
      "@testing-library/jest-dom"
    ]
  },
  "include": [
    "src",
    "vite.config.ts"
  ]
}
````

---

# File: `vite.config.ts`

````typescript
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_PROXY_TARGET ?? "http://backend:8000",
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
````
