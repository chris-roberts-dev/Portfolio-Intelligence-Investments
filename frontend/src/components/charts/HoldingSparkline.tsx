import type { EChartsOption } from "echarts";
import { LineChart } from "echarts/charts";
import { AriaComponent, GridComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useMemo, useRef } from "react";

import {
  formatCurrency,
  formatDate,
} from "../../features/dashboard/formatting";
import type { HoldingSparklinePoint } from "../../types/dashboard";
import { chartTheme } from "./chartTheme";
import { useECharts } from "./useECharts";

echarts.use([
  LineChart,
  AriaComponent,
  GridComponent,
  CanvasRenderer,
]);

interface HoldingSparklineProps {
  points: HoldingSparklinePoint[];
  symbol: string;
  currency: string;
}

interface SparklineRow {
  date: string;
  value: number | null;
}

function toFiniteNumber(value: string | null): number | null {
  if (value === null) {
    return null;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function sparklineSummary(
  rows: SparklineRow[],
  symbol: string,
  currency: string,
): string {
  const available = rows.filter(
    (row): row is SparklineRow & { value: number } =>
      row.value !== null,
  );
  const missingCount = rows.length - available.length;

  if (available.length === 0) {
    return `${symbol} has no selected-period sparkline prices.`;
  }

  const first = available[0];
  const last = available[available.length - 1];

  if (!first || !last) {
    return `${symbol} selected-period sparkline data is unavailable.`;
  }

  const missingText =
    missingCount > 0
      ? ` ${missingCount} trading-session observation${missingCount === 1 ? " is" : "s are"} missing and not interpolated.`
      : "";

  return `${symbol} adjusted close moved from ${formatCurrency(
    String(first.value),
    currency,
  )} on ${formatDate(first.date)} to ${formatCurrency(
    String(last.value),
    currency,
  )} on ${formatDate(last.date)}.${missingText}`;
}

export function HoldingSparkline({
  points,
  symbol,
  currency,
}: HoldingSparklineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rows = useMemo<SparklineRow[]>(
    () =>
      points.map((point) => ({
        date: point.observation_date,
        value: toFiniteNumber(point.adjusted_close),
      })),
    [points],
  );
  const summary = useMemo(
    () => sparklineSummary(rows, symbol, currency),
    [currency, rows, symbol],
  );

  const option = useMemo<EChartsOption | null>(() => {
    if (rows.length === 0) {
      return null;
    }

    return {
      animation: true,
      aria: {
        enabled: true,
        description: summary,
      },
      grid: {
        left: 1,
        right: 1,
        top: 3,
        bottom: 3,
      },
      xAxis: {
        type: "time",
        show: false,
      },
      yAxis: {
        type: "value",
        show: false,
        scale: true,
      },
      series: [
        {
          type: "line" as const,
          showSymbol: false,
          connectNulls: false,
          smooth: false,
          silent: true,
          lineStyle: {
            width: 1.75,
            color: chartTheme.primary,
          },
          data: rows.map((row) => [row.date, row.value]),
        },
      ],
    };
  }, [rows, summary]);

  useECharts(containerRef, option, {
    enabled: rows.length > 0,
  });

  if (rows.length === 0) {
    return <span className="text-xs text-slate-500">No history</span>;
  }

  return (
    <div className="min-w-0">
      <div
        ref={containerRef}
        className="h-12 w-full min-w-24"
        role="img"
        aria-label={summary}
      />
      <span className="sr-only">{summary}</span>
    </div>
  );
}
