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
