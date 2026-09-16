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

import { formatDate } from "../../features/dashboard/formatting";
import type { MarketBarSymbolResult } from "../../types/marketData";
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

interface MarketPriceChartProps {
  results: MarketBarSymbolResult[];
}

function formatPrice(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "Not available";
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(value);
}

export function MarketPriceChart({
  results,
}: MarketPriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const successful = useMemo(
    () =>
      results.filter(
        (result) =>
          result.status === "SUCCEEDED" && result.bars.length > 0,
      ),
    [results],
  );

  const option = useMemo<EChartsOption | null>(() => {
    if (successful.length === 0) {
      return null;
    }

    return {
      animation: true,
      aria: {
        enabled: true,
        description:
          "Daily raw close prices for successful market-data symbols. Missing close values remain gaps and are not interpolated.",
      },
      grid: {
        left: 12,
        right: 18,
        top: 42,
        bottom: 18,
        containLabel: true,
      },
      legend: {
        top: 0,
        left: 0,
        textStyle: { color: chartTheme.axisText },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: chartTheme.tooltipBackground,
        borderWidth: 0,
        textStyle: { color: chartTheme.tooltipText },
      },
      xAxis: {
        type: "time",
        axisLine: {
          lineStyle: { color: chartTheme.gridline },
        },
        axisLabel: { color: chartTheme.axisText },
      },
      yAxis: {
        type: "value",
        scale: true,
        axisLabel: { color: chartTheme.axisText },
        splitLine: {
          lineStyle: { color: chartTheme.gridline },
        },
      },
      series: successful.map((result) => ({
        name: result.symbol,
        type: "line" as const,
        showSymbol: false,
        connectNulls: false,
        smooth: false,
        data: result.bars.map((bar) => [bar.trade_date, bar.close]),
      })),
    };
  }, [successful]);

  useECharts(containerRef, option, {
    enabled: successful.length > 0,
  });

  if (successful.length === 0) {
    return null;
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-80 w-full"
        role="img"
        tabIndex={0}
        aria-label="Daily raw close price chart"
      />

      <details className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">
          View raw price data
        </summary>

        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">Symbol</th>
                <th className="py-2 pr-4 font-semibold">Date</th>
                <th className="py-2 pr-4 font-semibold">Close</th>
                <th className="py-2 pr-4 font-semibold">Source</th>
              </tr>
            </thead>
            <tbody>
              {successful.flatMap((result) =>
                result.bars.map((bar) => (
                  <tr
                    key={`${result.symbol}-${bar.trade_date}`}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="py-2 pr-4 font-semibold text-slate-900">
                      {result.symbol}
                    </td>
                    <td className="py-2 pr-4 text-slate-700">
                      {formatDate(bar.trade_date)}
                    </td>
                    <td className="py-2 pr-4 tabular-nums text-slate-700">
                      {formatPrice(bar.close)}
                    </td>
                    <td className="py-2 pr-4 text-slate-700">
                      {bar.source}
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
