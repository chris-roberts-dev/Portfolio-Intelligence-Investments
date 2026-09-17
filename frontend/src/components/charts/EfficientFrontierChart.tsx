import type { EChartsOption } from "echarts";
import { ScatterChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useMemo, useRef } from "react";

import type { OptimizedPortfolioResult } from "../../types/optimization";
import { chartTheme } from "./chartTheme";
import { useECharts } from "./useECharts";

echarts.use([
  ScatterChart,
  AriaComponent,
  GridComponent,
  TooltipComponent,
  CanvasRenderer,
]);

interface EfficientFrontierChartProps {
  points: OptimizedPortfolioResult[];
  assetLabels: ReadonlyMap<string, string>;
}

function formatPercent(
  value: number | null,
): string {
  if (
    value === null ||
    !Number.isFinite(value)
  ) {
    return "Not available";
  }

  return new Intl.NumberFormat(
    undefined,
    {
      style: "percent",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    },
  ).format(value);
}

function formatRatio(
  value: number | null,
): string {
  if (
    value === null ||
    !Number.isFinite(value)
  ) {
    return "Not available";
  }

  return new Intl.NumberFormat(
    undefined,
    {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    },
  ).format(value);
}

function axisPercent(
  value: number,
): string {
  return `${new Intl.NumberFormat(
    undefined,
    {
      maximumFractionDigits: 1,
    },
  ).format(value * 100)}%`;
}

export function EfficientFrontierChart({
  points,
  assetLabels,
}: EfficientFrontierChartProps) {
  const containerRef =
    useRef<HTMLDivElement | null>(null);

  const option =
    useMemo<EChartsOption | null>(() => {
      if (points.length === 0) {
        return null;
      }

      return {
        animation: true,
        aria: {
          enabled: true,
          description:
            "Server-provided efficient frontier points with expected annual volatility on the horizontal axis and expected annual return on the vertical axis. No points are interpolated in the browser.",
        },
        grid: {
          left: 12,
          right: 18,
          top: 18,
          bottom: 18,
          containLabel: true,
        },
        tooltip: {
          trigger: "item",
          backgroundColor:
            chartTheme.tooltipBackground,
          borderWidth: 0,
          textStyle: {
            color:
              chartTheme.tooltipText,
          },
          formatter: (
            params: unknown,
          ) => {
            const item =
              Array.isArray(params)
                ? params[0]
                : params;

            const rawValue =
              item !== null &&
              typeof item ===
                "object" &&
              "value" in item
                ? (
                    item as {
                      value?: unknown;
                    }
                  ).value
                : null;

            const value =
              Array.isArray(rawValue)
                ? rawValue
                : [];

            const volatility =
              typeof value[0] ===
              "number"
                ? value[0]
                : null;

            const expectedReturn =
              typeof value[1] ===
              "number"
                ? value[1]
                : null;

            return (
              `Expected volatility: ${formatPercent(volatility)}` +
              `<br/>Expected return: ${formatPercent(expectedReturn)}`
            );
          },
        },
        xAxis: {
          type: "value",
          name: "Expected volatility",
          nameLocation: "middle",
          nameGap: 30,
          axisLabel: {
            color:
              chartTheme.axisText,
            formatter: (
              value: unknown,
            ) =>
              axisPercent(
                Number(value),
              ),
          },
          splitLine: {
            lineStyle: {
              color:
                chartTheme.gridline,
            },
          },
        },
        yAxis: {
          type: "value",
          name: "Expected return",
          nameLocation: "middle",
          nameGap: 44,
          axisLabel: {
            color:
              chartTheme.axisText,
            formatter: (
              value: unknown,
            ) =>
              axisPercent(
                Number(value),
              ),
          },
          splitLine: {
            lineStyle: {
              color:
                chartTheme.gridline,
            },
          },
        },
        series: [
          {
            name: "Efficient frontier",
            type: "scatter",
            symbolSize: 10,
            data: points.map(
              (point) => [
                point.expected_volatility,
                point.expected_return,
              ],
            ),
          },
        ],
      };
    }, [points]);

  useECharts(
    containerRef,
    option,
    {
      enabled: points.length > 0,
    },
  );

  if (points.length === 0) {
    return null;
  }

  return (
    <div>
      <div
        ref={containerRef}
        className="h-[28rem] w-full"
        role="img"
        tabIndex={0}
        aria-label="Efficient frontier expected return and volatility chart"
      />

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[880px] border-collapse text-left text-xs">
          <caption className="sr-only">
            Every efficient-frontier
            point returned by the
            optimization server.
          </caption>

          <thead>
            <tr className="border-b border-slate-200 text-slate-500">
              <th className="py-2 pr-4 font-semibold">
                Point
              </th>
              <th className="py-2 pr-4 font-semibold">
                Target return
              </th>
              <th className="py-2 pr-4 font-semibold">
                Expected return
              </th>
              <th className="py-2 pr-4 font-semibold">
                Expected volatility
              </th>
              <th className="py-2 pr-4 font-semibold">
                Sharpe ratio
              </th>
              <th className="py-2 font-semibold">
                Server weights
              </th>
            </tr>
          </thead>

          <tbody>
            {points.map(
              (point, index) => (
                <tr
                  key={`${point.target_return ?? "none"}-${index}`}
                  className="border-b border-slate-100 align-top last:border-0"
                >
                  <th className="py-2 pr-4 font-semibold text-slate-900">
                    {index + 1}
                  </th>

                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatPercent(
                      point.target_return,
                    )}
                  </td>

                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatPercent(
                      point.expected_return,
                    )}
                  </td>

                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatPercent(
                      point.expected_volatility,
                    )}
                  </td>

                  <td className="py-2 pr-4 tabular-nums text-slate-700">
                    {formatRatio(
                      point.sharpe_ratio,
                    )}
                  </td>

                  <td className="py-2 text-slate-700">
                    {point.weights
                      .map(
                        (weight) =>
                          `${
                            assetLabels.get(
                              weight.asset_id,
                            ) ??
                            weight.asset_id
                          }: ${formatPercent(
                            weight.weight,
                          )}`,
                      )
                      .join(" · ")}
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}