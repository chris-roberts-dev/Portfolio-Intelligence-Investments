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
