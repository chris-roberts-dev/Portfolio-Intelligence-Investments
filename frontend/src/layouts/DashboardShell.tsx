import type { PropsWithChildren, ReactNode } from "react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router";

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

function MarketDataIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M4 18V9m5 9V5m5 13v-7m5 7V3" />
    </svg>
  );
}

function navLinkClass(active: boolean): string {
  return `flex h-11 w-11 items-center justify-center rounded-xl outline-none transition focus-visible:ring-2 focus-visible:ring-blue-400 ${
    active
      ? "bg-slate-800 text-white"
      : "text-slate-300 hover:bg-slate-800 hover:text-white"
  }`;
}

export function DashboardShell({
  header,
  children,
}: DashboardShellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const sessionQuery = useSession();
  const logoutMutation = useLogout();
  const user = sessionQuery.data?.user;
  const marketDataActive = location.pathname.startsWith("/market-data");
  const overviewActive = !marketDataActive;

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

        <nav
          className="mt-10 flex flex-col gap-2"
          aria-label="Primary navigation"
        >
          <Link
            to="/"
            className={navLinkClass(overviewActive)}
            aria-label="Overview"
            title="Overview"
            aria-current={overviewActive ? "page" : undefined}
          >
            <OverviewIcon />
          </Link>

          <Link
            to="/market-data"
            className={navLinkClass(marketDataActive)}
            aria-label="Market data"
            title="Market data"
            aria-current={marketDataActive ? "page" : undefined}
          >
            <MarketDataIcon />
          </Link>
        </nav>
      </aside>

      <div className="md:pl-20">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="border-b border-slate-100 bg-slate-50/90">
            <div className="mx-auto flex min-h-9 w-full max-w-[1600px] items-center justify-between gap-3 px-4 py-1.5 text-xs sm:px-6 lg:px-8">
              <nav
                className="flex items-center gap-3 md:hidden"
                aria-label="Mobile primary navigation"
              >
                <Link
                  to="/"
                  className={
                    overviewActive
                      ? "font-semibold text-slate-950"
                      : "font-semibold text-slate-600 hover:text-slate-950"
                  }
                  aria-current={overviewActive ? "page" : undefined}
                >
                  Overview
                </Link>
                <Link
                  to="/market-data"
                  className={
                    marketDataActive
                      ? "font-semibold text-slate-950"
                      : "font-semibold text-slate-600 hover:text-slate-950"
                  }
                  aria-current={marketDataActive ? "page" : undefined}
                >
                  Market data
                </Link>
              </nav>

              <div className="flex items-center justify-end gap-3">
              {user ? (
                <span
                  className="max-w-56 truncate text-slate-500"
                  title={user.email}
                >
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
                {logoutMutation.isPending
                  ? "Signing out…"
                  : "Sign out"}
              </button>

              {logoutMutation.error instanceof Error ? (
                <span role="alert" className="text-rose-700">
                  Sign out failed.
                </span>
              ) : null}
              </div>
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
