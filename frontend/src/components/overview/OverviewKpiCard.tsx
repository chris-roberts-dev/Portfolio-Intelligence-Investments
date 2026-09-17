import type { ReactNode } from "react";

interface OverviewKpiCardProps {
  label: string;
  value: string;
  context?: ReactNode;
  valueTone?: "neutral" | "positive" | "negative";
}

export function OverviewKpiCard({
  label,
  value,
  context,
  valueTone = "neutral",
}: OverviewKpiCardProps) {
  const toneClass =
    valueTone === "positive"
      ? "text-emerald-700"
      : valueTone === "negative"
        ? "text-rose-700"
        : "text-slate-950";

  return (
    <article className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p
        className={`mt-2 break-words text-2xl font-semibold tracking-tight tabular-nums ${toneClass}`}
      >
        {value}
      </p>
      {context ? (
        <div className="mt-1.5 min-h-5 text-xs leading-5 text-slate-500">
          {context}
        </div>
      ) : null}
    </article>
  );
}
