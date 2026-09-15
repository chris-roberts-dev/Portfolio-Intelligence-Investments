import type { EChartsOption } from "echarts";
import { BarChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import { formatCurrency } from "../../features/dashboard/formatting";
import type { DashboardAllocationGroup } from "../../types/dashboard";
import { chartTheme } from "./chartTheme";

echarts.use([
  BarChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

const ALLOCATION_COLORS = [
  "#2563eb",
  "#0f766e",
  "#7c3aed",
  "#d97706",
  "#475569",
] as const;

interface AllocationChartProps {
  groups: DashboardAllocationGroup[];
  currency: string;
}

function formatWeight(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function seriesNameFromParams(params: unknown): string | null {
  const first = Array.isArray(params) ? params[0] : params;

  if (
    first === null ||
    typeof first !== "object" ||
    !("seriesName" in first)
  ) {
    return null;
  }

  return typeof first.seriesName === "string" ? first.seriesName : null;
}

export function AllocationChart({ groups, currency }: AllocationChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const weightedGroups = useMemo(
    () => groups.filter((group) => group.weight !== null),
    [groups],
  );

  useEffect(() => {
    const container = containerRef.current;

    if (container === null || weightedGroups.length === 0) {
      return undefined;
    }

    const chart = echarts.init(container, undefined, {
      renderer: "canvas",
    });
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const option: EChartsOption = {
      animation: !reduceMotion,
      aria: {
        enabled: true,
        decal: {
          show: true,
        },
        description:
          "Current portfolio allocation by backend-authoritative asset class and cash weight.",
      },
      color: [...ALLOCATION_COLORS],
      grid: {
        left: 8,
        right: 8,
        top: 44,
        bottom: 28,
        containLabel: true,
      },
      legend: {
        top: 0,
        left: 0,
        textStyle: {
          color: chartTheme.axisText,
          fontSize: 12,
        },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "shadow",
        },
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: {
          color: chartTheme.tooltipText,
        },
        formatter: (params: unknown) => {
          const seriesName = seriesNameFromParams(params);
          const group = weightedGroups.find(
            (candidate) => candidate.label === seriesName,
          );

          if (group === undefined) {
            return "";
          }

          return [
            `<strong>${escapeHtml(group.label)}</strong>`,
            escapeHtml(formatCurrency(group.market_value, currency)),
            escapeHtml(formatWeight(group.weight)),
          ].join("<br />");
        },
      },
      xAxis: {
        type: "value",
        min: 0,
        max: 1,
        axisLabel: {
          color: chartTheme.axisText,
          formatter: (value: string | number) =>
            `${Math.round(Number(value) * 100)}%`,
        },
        splitLine: {
          lineStyle: {
            color: chartTheme.gridline,
          },
        },
      },
      yAxis: {
        type: "category",
        data: ["Portfolio"],
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: { show: false },
      },
      series: weightedGroups.map((group, index) => ({
        name: group.label,
        type: "bar" as const,
        stack: "allocation",
        barWidth: 34,
        data: [group.weight],
        itemStyle: {
          color: ALLOCATION_COLORS[index % ALLOCATION_COLORS.length],
          borderRadius:
            index === 0
              ? [8, 0, 0, 8]
              : index === weightedGroups.length - 1
                ? [0, 8, 8, 0]
                : 0,
        },
        emphasis: {
          focus: "series" as const,
        },
      })),
    };

    chart.setOption(option);

    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [currency, weightedGroups]);

  if (weightedGroups.length === 0) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="h-40 w-full"
      role="img"
      aria-label="Portfolio allocation chart"
    />
  );
}
