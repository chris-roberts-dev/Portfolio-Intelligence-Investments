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
import { useEffect, useMemo, useRef } from "react";

import { formatCurrency, formatDate, formatPercent } from "../../features/dashboard/formatting";
import type { DashboardPerformanceResult } from "../../types/dashboard";
import { chartTheme } from "./chartTheme";

export type PerformanceChartMode = "VALUE" | "RETURN";

echarts.use([
  LineChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface PerformanceChartProps {
  performance: DashboardPerformanceResult;
  currency: string;
  mode: PerformanceChartMode;
}

interface ChartRow {
  date: string;
  portfolioValue: number | null;
  portfolioReturn: number | null;
  benchmarkReturn: number | null;
  quality: string;
}

function toFiniteNumber(value: string | null): number | null {
  if (value === null) {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function PerformanceChart({
  performance,
  currency,
  mode,
}: PerformanceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rows = useMemo<ChartRow[]>(() => {
    const benchmarkByDate = new Map(
      performance.benchmark_points.map((point) => [
        point.observation_date,
        point.cumulative_return,
      ]),
    );

    return performance.points.map((point) => ({
      date: point.observation_date,
      portfolioValue: toFiniteNumber(point.portfolio_value),
      portfolioReturn: point.cumulative_return,
      benchmarkReturn: benchmarkByDate.get(point.observation_date) ?? null,
      quality: point.data_quality,
    }));
  }, [performance]);

  useEffect(() => {
    const container = containerRef.current;

    if (container === null || rows.length === 0) {
      return undefined;
    }

    const chart = echarts.init(container);
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const isReturnMode = mode === "RETURN";
    const portfolioData = rows.map((row) => [
      row.date,
      isReturnMode ? row.portfolioReturn : row.portfolioValue,
    ]);
    const benchmarkData = rows.map((row) => [row.date, row.benchmarkReturn]);

    const option: EChartsOption = {
      animation: !reduceMotion,
      aria: {
        enabled: true,
        description: isReturnMode
          ? "Portfolio cumulative return over the selected period."
          : "Portfolio market value over the selected period.",
      },
      grid: {
        left: 12,
        right: 18,
        top: isReturnMode && performance.benchmark_points.length > 0 ? 42 : 20,
        bottom: 16,
        containLabel: true,
      },
      legend: {
        show: isReturnMode && performance.benchmark_points.length > 0,
        top: 0,
        right: 0,
        textStyle: { color: chartTheme.axisText },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: { color: chartTheme.tooltipText },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) {
            return "";
          }

          const first = params[0] as { data?: unknown };
          const pair = Array.isArray(first.data) ? first.data : [];
          const date = typeof pair[0] === "string" ? pair[0] : "";
          const row = rows.find((candidate) => candidate.date === date);

          if (!row) {
            return "";
          }

          const portfolioLabel = isReturnMode
            ? formatPercent(row.portfolioReturn)
            : formatCurrency(
                row.portfolioValue === null ? null : String(row.portfolioValue),
                currency,
              );
          const benchmarkLabel =
            isReturnMode && row.benchmarkReturn !== null
              ? `<br/>Benchmark: ${formatPercent(row.benchmarkReturn)}`
              : "";

          return `${formatDate(row.date)}<br/>Portfolio: ${portfolioLabel}${benchmarkLabel}<br/>Data: ${row.quality}`;
        },
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
            isReturnMode
              ? `${(value * 100).toFixed(0)}%`
              : new Intl.NumberFormat(undefined, {
                  notation: "compact",
                  maximumFractionDigits: 1,
                }).format(value),
        },
        splitLine: {
          lineStyle: { color: chartTheme.gridline },
        },
      },
      series: [
        {
          name: "Portfolio",
          type: "line",
          showSymbol: false,
          connectNulls: false,
          smooth: false,
          lineStyle: { width: 2.5, color: chartTheme.primary },
          itemStyle: { color: chartTheme.primary },
          areaStyle: isReturnMode
            ? undefined
            : { color: "rgba(37, 99, 235, 0.08)" },
          data: portfolioData,
        },
        ...(isReturnMode && performance.benchmark_points.length > 0
          ? [
              {
                name: performance.provenance.benchmark_symbol ?? "Benchmark",
                type: "line" as const,
                showSymbol: false,
                connectNulls: false,
                smooth: false,
                lineStyle: {
                  width: 1.75,
                  type: "dashed" as const,
                  color: chartTheme.benchmark,
                },
                itemStyle: { color: chartTheme.benchmark },
                data: benchmarkData,
              },
            ]
          : []),
      ],
    };
    chart.setOption(option);

    const resize = () => chart.resize();
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(resize);

    observer?.observe(container);
    window.addEventListener("resize", resize);

    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", resize);
      chart.dispose();
    };
  }, [currency, mode, performance, rows]);

  if (rows.length === 0) {
    return null;
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-72 w-full sm:h-80"
        role="img"
        tabIndex={0}
        aria-label={
          mode === "RETURN"
            ? "Portfolio cumulative return chart"
            : "Portfolio market value chart"
        }
      />

      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          View chart data
        </summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">Date</th>
                <th className="py-2 pr-4 font-semibold">Portfolio value</th>
                <th className="py-2 pr-4 font-semibold">Portfolio return</th>
                <th className="py-2 pr-4 font-semibold">Benchmark return</th>
                <th className="py-2 font-semibold">Quality</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.date} className="border-b border-slate-100 last:border-0">
                  <td className="py-2 pr-4 text-slate-700">{formatDate(row.date)}</td>
                  <td className="py-2 pr-4 text-slate-700">
                    {formatCurrency(
                      row.portfolioValue === null ? null : String(row.portfolioValue),
                      currency,
                    )}
                  </td>
                  <td className="py-2 pr-4 text-slate-700">
                    {formatPercent(row.portfolioReturn)}
                  </td>
                  <td className="py-2 pr-4 text-slate-700">
                    {formatPercent(row.benchmarkReturn)}
                  </td>
                  <td className="py-2 text-slate-700">{row.quality}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
