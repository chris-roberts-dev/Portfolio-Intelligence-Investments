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
