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
