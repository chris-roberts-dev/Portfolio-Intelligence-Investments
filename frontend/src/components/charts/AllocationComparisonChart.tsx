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
import { useMemo, useRef } from "react";

import { chartTheme } from "./chartTheme";
import { useECharts } from "./useECharts";

echarts.use([
  BarChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

export interface AllocationComparisonRow {
  assetId: string;
  label: string;
  currentWeight: number | null;
  equalWeight: number | null;
  minimumVarianceWeight: number | null;
  maximumSharpeWeight: number | null;
}

interface AllocationComparisonChartProps {
  rows: AllocationComparisonRow[];
  baselineLabel?: string;
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function chartPercent(value: number): string {
  return `${new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
  }).format(value * 100)}%`;
}

export function AllocationComparisonChart({
  rows,
  baselineLabel = "Current observed",
}: AllocationComparisonChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const option = useMemo<EChartsOption | null>(() => {
    if (rows.length === 0) {
      return null;
    }

    return {
      animation: true,
      aria: {
        enabled: true,
        description:
          `${baselineLabel} allocation compared with available persisted server optimization allocations. Missing optimization runs remain gaps.`,
      },
      grid: {
        left: 12,
        right: 18,
        top: 48,
        bottom: 18,
        containLabel: true,
      },
      legend: {
        top: 0,
        left: 0,
        textStyle: {
          color: chartTheme.axisText,
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
        valueFormatter: (value: unknown) =>
          typeof value === "number"
            ? chartPercent(value)
            : "Not available",
      },
      xAxis: {
        type: "value",
        min: 0,
        max: 1,
        axisLabel: {
          color: chartTheme.axisText,
          formatter: (value: unknown) =>
            chartPercent(Number(value)),
        },
        splitLine: {
          lineStyle: {
            color: chartTheme.gridline,
          },
        },
      },
      yAxis: {
        type: "category",
        data: rows.map((row) => row.label),
        axisLabel: {
          color: chartTheme.axisText,
        },
        axisLine: {
          lineStyle: {
            color: chartTheme.gridline,
          },
        },
      },
      series: [
        {
          name: baselineLabel,
          type: "bar",
          data: rows.map(
            (row) => row.currentWeight,
          ),
        },
        {
          name: "Equal weight",
          type: "bar",
          data: rows.map(
            (row) => row.equalWeight,
          ),
        },
        {
          name: "Minimum variance",
          type: "bar",
          data: rows.map(
            (row) =>
              row.minimumVarianceWeight,
          ),
        },
        {
          name: "Maximum Sharpe",
          type: "bar",
          data: rows.map(
            (row) =>
              row.maximumSharpeWeight,
          ),
        },
      ],
    };
  }, [baselineLabel, rows]);

  useECharts(containerRef, option, {
    enabled: rows.length > 0,
  });

  if (rows.length === 0) {
    return null;
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-[30rem] w-full"
        role="img"
        tabIndex={0}
        aria-label={`${baselineLabel} and optimized allocation comparison chart`}
      />

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left text-xs">
          <caption className="sr-only">
            {baselineLabel} allocation and available persisted optimization
            allocations by asset.
          </caption>

          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="py-2 pr-4 font-semibold">
                Asset
              </th>
              <th className="py-2 pr-4 font-semibold">
                {baselineLabel}
              </th>
              <th className="py-2 pr-4 font-semibold">
                Equal weight
              </th>
              <th className="py-2 pr-4 font-semibold">
                Minimum variance
              </th>
              <th className="py-2 font-semibold">
                Maximum Sharpe
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => (
              <tr
                key={row.assetId}
                className="border-b border-slate-100 last:border-0"
              >
                <th className="py-2 pr-4 font-semibold text-slate-900">
                  {row.label}
                </th>

                <td className="py-2 pr-4 tabular-nums text-slate-700">
                  {formatPercent(
                    row.currentWeight,
                  )}
                </td>

                <td className="py-2 pr-4 tabular-nums text-slate-700">
                  {formatPercent(
                    row.equalWeight,
                  )}
                </td>

                <td className="py-2 pr-4 tabular-nums text-slate-700">
                  {formatPercent(
                    row.minimumVarianceWeight,
                  )}
                </td>

                <td className="py-2 tabular-nums text-slate-700">
                  {formatPercent(
                    row.maximumSharpeWeight,
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}