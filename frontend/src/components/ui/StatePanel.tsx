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
