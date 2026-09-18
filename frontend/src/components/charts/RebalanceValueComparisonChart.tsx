import type { EChartsOption } from "echarts";
import { LineChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useMemo, useRef } from "react";

import { formatCurrency, formatDate } from "../../features/dashboard/formatting";
import { historicalValueChartSeries } from "../../features/rebalancing/rebalancingTransforms";
import type { HistoricalRebalanceComparison } from "../../types/rebalancing";
import { chartTheme } from "./chartTheme";
import { useECharts } from "./useECharts";

echarts.use([
  LineChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface RebalanceValueComparisonChartProps {
  comparison: HistoricalRebalanceComparison;
  currency: string;
}

function policyLabel(name: string): string {
  switch (name) {
    case "annual":
      return "Annual";
    case "quarterly":
      return "Quarterly";
    case "monthly":
      return "Monthly";
    case "threshold":
      return "Threshold";
    default:
      return name;
  }
}

export function RebalanceValueComparisonChart({
  comparison,
  currency,
}: RebalanceValueComparisonChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const series = useMemo(
    () => historicalValueChartSeries(comparison),
    [comparison],
  );

  const option = useMemo<EChartsOption | null>(() => {
    if (series.length === 0) {
      return null;
    }

    return {
      animation: true,
      aria: {
        enabled: true,
        description:
          "Historical portfolio value for each deterministic rebalancing policy.",
      },
      grid: {
        left: 12,
        right: 18,
        top: 48,
        bottom: 16,
        containLabel: true,
      },
      legend: {
        top: 0,
        right: 0,
        textStyle: { color: chartTheme.axisText },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: { color: chartTheme.tooltipText },
        valueFormatter: (value: unknown) =>
          typeof value === "number"
            ? formatCurrency(String(value), currency)
            : "Not available",
      },
      xAxis: {
        type: "time",
        axisLine: { lineStyle: { color: chartTheme.gridline } },
        axisLabel: { color: chartTheme.axisText },
        splitLine: { show: false },
      },
      yAxis: {
        type: "value",
        scale: true,
        axisLabel: {
          color: chartTheme.axisText,
          formatter: (value: number) =>
            new Intl.NumberFormat(undefined, {
              notation: "compact",
              maximumFractionDigits: 1,
            }).format(value),
        },
        splitLine: { lineStyle: { color: chartTheme.gridline } },
      },
      series: series.map((item) => ({
        name: policyLabel(item.name),
        type: "line" as const,
        showSymbol: false,
        connectNulls: false,
        smooth: false,
        lineStyle: { width: 2 },
        data: item.points,
      })),
    };
  }, [currency, series]);

  useECharts(containerRef, option, { enabled: series.length > 0 });

  if (series.length === 0) {
    return null;
  }

  const dates = comparison.result.aligned_dates;
  const valuesByPolicy = new Map(
    comparison.result.policies.map((policy) => [
      policy.name,
      new Map(
        policy.snapshots.map((snapshot) => [
          snapshot.trade_date,
          snapshot.total_value,
        ]),
      ),
    ]),
  );

  return (
    <div>
      <div
        ref={containerRef}
        className="h-72 w-full sm:h-80"
        role="img"
        tabIndex={0}
        aria-label="Historical rebalancing policy portfolio value comparison"
      />
      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          View chart data
        </summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">Date</th>
                {comparison.result.policies.map((policy) => (
                  <th key={policy.name} className="py-2 pr-4 font-semibold">
                    {policyLabel(policy.name)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dates.map((date) => (
                <tr key={date} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-4 text-slate-700">{formatDate(date)}</td>
                  {comparison.result.policies.map((policy) => (
                    <td key={policy.name} className="py-2 pr-4 text-slate-700">
                      {(() => {
                        const value = valuesByPolicy.get(policy.name)?.get(date);
                        return formatCurrency(
                          value === undefined ? null : String(value),
                          currency,
                        );
                      })()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
