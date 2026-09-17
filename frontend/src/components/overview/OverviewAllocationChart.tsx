import type { EChartsOption } from "echarts";
import { PieChart } from "echarts/charts";
import {
  AriaComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useMemo, useRef } from "react";

import type { DashboardAllocationGroup } from "../../types/dashboard";
import { chartTheme } from "../charts/chartTheme";
import { useECharts } from "../charts/useECharts";

echarts.use([
  PieChart,
  AriaComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface OverviewAllocationChartProps {
  groups: DashboardAllocationGroup[];
}

type AvailableAllocationGroup = DashboardAllocationGroup & {
  weight: number;
};

function hasAvailableWeight(
  group: DashboardAllocationGroup,
): group is AvailableAllocationGroup {
  return (
    group.weight !== null &&
    Number.isFinite(group.weight) &&
    group.weight > 0
  );
}

function formatAllocationWeight(
  value: number | null,
  fractionDigits = 1,
): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function OverviewAllocationChart({
  groups,
}: OverviewAllocationChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const availableGroups = useMemo(
    () => groups.filter(hasAvailableWeight),
    [groups],
  );

  const option = useMemo<EChartsOption | null>(() => {
    if (availableGroups.length === 0) {
      return null;
    }

    return {
      animation: true,
      aria: {
        enabled: true,
        description:
          "Current portfolio allocation by the server-provided grouping dimension.",
      },
      tooltip: {
        trigger: "item",
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: {
          color: chartTheme.tooltipText,
        },
        formatter: (params: unknown) => {
          if (params === null || typeof params !== "object") {
            return "";
          }

          const value =
            "value" in params && typeof params.value === "number"
              ? params.value
              : null;

          const name =
            "name" in params && typeof params.name === "string"
              ? params.name
              : "Allocation";

          return `${name}: ${formatAllocationWeight(value, 1)}`;
        },
      },
      legend: {
        orient: "vertical",
        right: 0,
        top: "middle",
        width: "42%",
        textStyle: {
          color: chartTheme.axisText,
        },
      },
      series: [
        {
          name: "Allocation",
          type: "pie",
          radius: ["50%", "76%"],
          center: ["32%", "50%"],
          avoidLabelOverlap: true,
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              formatter: "{b}\n{d}%",
              fontWeight: "bold",
            },
          },
          data: availableGroups.map((group) => ({
            name: group.label,
            value: group.weight,
          })),
        },
      ],
    };
  }, [availableGroups]);

  useECharts(containerRef, option, {
    enabled: availableGroups.length > 0,
  });

  if (availableGroups.length === 0) {
    return null;
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-64 w-full"
        role="img"
        tabIndex={0}
        aria-label="Current portfolio allocation chart"
      />

      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          View allocation data
        </summary>

        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[320px] text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">
                  Group
                </th>
                <th className="py-2 font-semibold">
                  Weight
                </th>
              </tr>
            </thead>

            <tbody>
              {availableGroups.map((group) => (
                <tr
                  key={group.key}
                  className="border-b border-slate-100 last:border-0"
                >
                  <td className="py-2 pr-4 font-medium text-slate-800">
                    {group.label}
                  </td>
                  <td className="py-2 tabular-nums text-slate-700">
                    {formatAllocationWeight(group.weight, 1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}