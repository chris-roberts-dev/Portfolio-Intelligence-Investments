import { useState, type PropsWithChildren, type ReactNode } from "react";
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router";

import { useLogout, useSession } from "../hooks/useAuth";

interface DashboardShellProps extends PropsWithChildren {
  header?: ReactNode;
  topBarStart?: ReactNode;
}

interface NavigationItem {
  to: string;
  label: string;
  ariaLabel?: string;
  active: boolean;
  icon: ReactNode;
}

function OverviewIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M4 13h6V4H4v9Zm0 7h6v-4H4v4Zm10 0h6v-9h-6v9Zm0-12h6V4h-6v4Z" />
    </svg>
  );
}

function PortfoliosIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M8 7V5.5A2.5 2.5 0 0 1 10.5 3h3A2.5 2.5 0 0 1 16 5.5V7m-11 0h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Zm-2 5h18" />
    </svg>
  );
}

function MarketDataIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M4 18V9m5 9V5m5 13v-7m5 7V3" />
    </svg>
  );
}

function AllocationLabIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M9 3v5l-5.5 9.5A2.3 2.3 0 0 0 5.5 21h13a2.3 2.3 0 0 0 2-3.5L15 8V3M7 13h10M8 3h8" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="m6 6 12 12M18 6 6 18" />
    </svg>
  );
}

function navLinkClass(active: boolean): string {
  return `group flex min-h-11 items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-sm font-medium outline-none transition focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 ${
    active
      ? "border-blue-400 bg-blue-600/20 text-white"
      : "border-transparent text-slate-300 hover:bg-slate-900 hover:text-white"
  }`;
}

function userInitials(
  firstName: string | undefined,
  lastName: string | undefined,
  email: string,
): string {
  const first = firstName?.trim().charAt(0) ?? "";
  const last = lastName?.trim().charAt(0) ?? "";
  const initials = `${first}${last}`.toUpperCase();

  if (initials) {
    return initials;
  }

  return email.trim().charAt(0).toUpperCase() || "U";
}

export function DashboardShell({
  header,
  topBarStart,
  children,
}: DashboardShellProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const sessionQuery = useSession();
  const logoutMutation = useLogout();
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const user = sessionQuery.data?.user;

  const allocationLabActive =
    location.pathname === "/allocation-lab" ||
    location.pathname.includes("/allocation-lab");
  const marketDataActive = location.pathname.startsWith("/market-data");
  const portfoliosActive =
    !allocationLabActive && location.pathname.startsWith("/portfolios");
  const overviewActive = location.pathname === "/";

  const navigationItems: NavigationItem[] = [
    {
      to: "/",
      label: "Overview",
      active: overviewActive,
      icon: <OverviewIcon />,
    },
    {
      to: "/portfolios",
      label: "Portfolios",
      active: portfoliosActive,
      icon: <PortfoliosIcon />,
    },
    {
      to: "/market-data",
      label: "Market Data",
      ariaLabel: "Market data",
      active: marketDataActive,
      icon: <MarketDataIcon />,
    },
    {
      to: "/allocation-lab",
      label: "Allocation Lab",
      active: allocationLabActive,
      icon: <AllocationLabIcon />,
    },
  ];

  async function handleLogout() {
    try {
      await logoutMutation.mutateAsync();
      navigate("/login", { replace: true });
    } catch {
      // Visible error copy below keeps the current protected view intact.
    }
  }

  const navigation = (
    <>
      <Link
        to="/"
        className="flex min-h-16 items-center gap-3 px-4 py-3 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-400"
        aria-label="Portfolio Intelligence home"
        onClick={() => setMobileNavigationOpen(false)}
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-sm font-bold text-white shadow-lg shadow-blue-950/30">
          PI
        </span>
        <span className="text-sm font-semibold leading-5 text-white">
          Portfolio
          <br />
          Intelligence
        </span>
      </Link>

      <nav className="mt-4 flex flex-col gap-1 px-2" aria-label="Primary navigation">
        {navigationItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={navLinkClass(item.active)}
            aria-label={item.ariaLabel}
            aria-current={item.active ? "page" : undefined}
            onClick={() => setMobileNavigationOpen(false)}
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="mt-auto border-t border-slate-800 px-4 py-4">
        <p className="truncate text-xs text-slate-400" title={user?.email}>
          {user?.email ?? "Authenticated workspace"}
        </p>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-slate-800 bg-slate-950 lg:flex">
        {navigation}
      </aside>

      {mobileNavigationOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/50"
            aria-label="Close navigation"
            onClick={() => setMobileNavigationOpen(false)}
          />
          <aside className="relative flex h-full w-72 max-w-[85vw] flex-col border-r border-slate-800 bg-slate-950 shadow-2xl">
            <button
              type="button"
              onClick={() => setMobileNavigationOpen(false)}
              className="absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-lg text-slate-300 outline-none hover:bg-slate-900 hover:text-white focus-visible:ring-2 focus-visible:ring-blue-400"
              aria-label="Close navigation panel"
            >
              <CloseIcon />
            </button>
            {navigation}
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="border-b border-slate-200">
            <div className="mx-auto flex min-h-14 w-full max-w-[1440px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
              <div className="flex min-w-0 items-center gap-3">
                <button
                  type="button"
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-blue-500 lg:hidden"
                  aria-label="Open navigation"
                  onClick={() => setMobileNavigationOpen(true)}
                >
                  <MenuIcon />
                </button>
                <div className="min-w-0">{topBarStart}</div>
              </div>

              <div className="flex items-center gap-3">
                {user ? (
                  <div className="hidden text-right sm:block">
                    <p className="max-w-48 truncate text-xs font-medium text-slate-700">
                      {user.first_name || user.last_name
                        ? `${user.first_name} ${user.last_name}`.trim()
                        : user.email}
                    </p>
                    <p className="max-w-48 truncate text-[11px] text-slate-500">
                      {user.email}
                    </p>
                  </div>
                ) : null}

                {user ? (
                  <span
                    className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700"
                    aria-hidden="true"
                  >
                    {userInitials(user.first_name, user.last_name, user.email)}
                  </span>
                ) : null}

                <button
                  type="button"
                  onClick={() => void handleLogout()}
                  disabled={logoutMutation.isPending}
                  className="rounded-lg px-2 py-2 text-xs font-semibold text-slate-600 outline-none hover:bg-slate-100 hover:text-slate-950 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
                >
                  {logoutMutation.isPending ? "Signing out…" : "Sign out"}
                </button>
              </div>
            </div>
          </div>

          {header}
        </header>

        {logoutMutation.error instanceof Error ? (
          <div className="mx-auto mt-3 w-full max-w-[1440px] px-4 sm:px-6 lg:px-8">
            <div
              className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
              role="alert"
            >
              Sign out failed. Your current authenticated view is still available.
            </div>
          </div>
        ) : null}

        <main className="mx-auto w-full max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          {children}
        </main>
      </div>
    </div>
  );
}
