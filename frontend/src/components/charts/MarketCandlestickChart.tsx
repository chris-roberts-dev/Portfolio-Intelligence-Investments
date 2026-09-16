import type { EChartsOption } from "echarts";
import { BarChart, CandlestickChart } from "echarts/charts";
import {
  AriaComponent,
  AxisPointerComponent,
  GridComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useMemo, useRef } from "react";

import { formatDate } from "../../features/dashboard/formatting";
import { buildCandlestickRows } from "../../features/marketData/marketDataTransforms";
import type { MarketBarSymbolResult } from "../../types/marketData";
import { chartTheme } from "./chartTheme";
import { useECharts } from "./useECharts";

echarts.use([
  CandlestickChart,
  BarChart,
  AriaComponent,
  AxisPointerComponent,
  GridComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface MarketCandlestickChartProps {
  result: MarketBarSymbolResult;
}

function formatNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value);
}

function formatVolume(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0,
  }).format(value);
}

export function MarketCandlestickChart({
  result,
}: MarketCandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rows = useMemo(
    () => buildCandlestickRows(result.bars),
    [result.bars],
  );

  const option = useMemo<EChartsOption | null>(() => {
    if (rows.length === 0) {
      return null;
    }

    const dates = rows.map((row) => row.date);

    return {
      animation: true,
      aria: {
        enabled: true,
        description: `${result.symbol} daily OHLC candlesticks with volume. Incomplete OHLC bars are omitted rather than filled.`,
      },
      axisPointer: {
        link: [{ xAxisIndex: "all" }],
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: { color: chartTheme.tooltipText },
      },
      grid: [
        {
          left: 12,
          right: 18,
          top: 18,
          height: "62%",
          containLabel: true,
        },
        {
          left: 12,
          right: 18,
          top: "76%",
          height: "16%",
          containLabel: true,
        },
      ],
      xAxis: [
        {
          type: "category",
          data: dates,
          boundaryGap: true,
          axisLine: {
            lineStyle: { color: chartTheme.gridline },
          },
          axisLabel: { color: chartTheme.axisText },
        },
        {
          type: "category",
          gridIndex: 1,
          data: dates,
          boundaryGap: true,
          axisLine: {
            lineStyle: { color: chartTheme.gridline },
          },
          axisLabel: { show: false },
        },
      ],
      yAxis: [
        {
          type: "value",
          scale: true,
          axisLabel: { color: chartTheme.axisText },
          splitLine: {
            lineStyle: { color: chartTheme.gridline },
          },
        },
        {
          type: "value",
          gridIndex: 1,
          scale: true,
          axisLabel: { color: chartTheme.axisText },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: `${result.symbol} OHLC`,
          type: "candlestick",
          data: rows.map((row) => row.value),
        },
        {
          name: `${result.symbol} volume`,
          type: "bar",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: rows.map((row) => row.volume),
        },
      ],
    };
  }, [result.symbol, rows]);

  useECharts(containerRef, option, {
    enabled: rows.length > 0,
  });

  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No complete OHLC observations are available for candlestick display.
      </p>
    );
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-[28rem] w-full"
        role="img"
        tabIndex={0}
        aria-label={`${result.symbol} candlestick and volume chart`}
      />

      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          View candlestick data
        </summary>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[680px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">Date</th>
                <th className="py-2 pr-4 font-semibold">Open</th>
                <th className="py-2 pr-4 font-semibold">Close</th>
                <th className="py-2 pr-4 font-semibold">Low</th>
                <th className="py-2 pr-4 font-semibold">High</th>
                <th className="py-2 font-semibold">Volume</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.date}
                  className="border-b border-slate-100 last:border-0"
                >
                  <td className="py-2 pr-4 text-slate-700">
                    {formatDate(row.date)}
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatNumber(row.value[0])}
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatNumber(row.value[1])}
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatNumber(row.value[2])}
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatNumber(row.value[3])}
                  </td>
                  <td className="py-2 tabular-nums text-slate-700">
                    {formatVolume(row.volume)}
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
