import { Route, Routes } from "react-router";

import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { AllocationLabPage } from "./pages/AllocationLabPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HoldingDetailPage } from "./pages/HoldingDetailPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { MarketDataExplorerPage } from "./pages/MarketDataExplorerPage";
import { PortfolioAnalysisPage } from "./pages/PortfolioAnalysisPage";
import { PortfolioManagementPage } from "./pages/PortfolioManagementPage";
import { PortfoliosPage } from "./pages/PortfoliosPage";

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
        <Route path="/portfolios" element={<PortfoliosPage />} />

        <Route
          path="/portfolios/:portfolioId/dashboard"
          element={<DashboardPage />}
        />

        <Route
          path="/portfolios/:portfolioId/analysis"
          element={<PortfolioAnalysisPage />}
        />

        <Route path="/allocation-lab" element={<AllocationLabPage />} />

        <Route
          path="/portfolios/:portfolioId/allocation-lab"
          element={<AllocationLabPage />}
        />

        <Route
          path="/portfolios/:portfolioId/manage"
          element={<PortfolioManagementPage />}
        />

        <Route
          path="/portfolios/:portfolioId/holdings/:assetId"
          element={<HoldingDetailPage />}
        />

        <Route path="/market-data" element={<MarketDataExplorerPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
