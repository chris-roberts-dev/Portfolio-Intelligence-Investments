import type { ReactNode } from "react";

interface DomainPageHeaderProps {
  title: string;
  description: string;
  eyebrow?: string;
  actions?: ReactNode;
}

export function DomainPageHeader({
  title,
  description,
  eyebrow,
  actions,
}: DomainPageHeaderProps) {
  return (
    <div
      className="mx-auto flex min-h-24 w-full max-w-[1440px] flex-wrap items-center gap-4 px-4 py-4 sm:px-6 lg:px-8"
      data-ui="domain-page-header"
    >
      <div className="min-w-0 flex-1">
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
            {eyebrow}
          </p>
        ) : null}
        <h1 className={`${eyebrow ? "mt-1 " : ""}text-3xl font-semibold tracking-tight text-slate-950`}>
          {title}
        </h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
          {description}
        </p>
      </div>
      {actions ? (
        <div className="flex w-full flex-wrap items-center justify-end gap-3 xl:w-auto">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
