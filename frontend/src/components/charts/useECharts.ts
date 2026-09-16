import type { EChartsOption } from "echarts";
import * as echarts from "echarts/core";
import type { RefObject } from "react";
import { useEffect, useRef } from "react";

import { chartThemeName, echartsTheme } from "./chartTheme";

interface UseEChartsOptions {
  enabled?: boolean;
}

echarts.registerTheme(chartThemeName, echartsTheme);

function prefersReducedMotion(): boolean {
  return (
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false
  );
}

function optionForMotionPreference(option: EChartsOption): EChartsOption {
  if (!prefersReducedMotion()) {
    return option;
  }

  return {
    ...option,
    animation: false,
    animationDuration: 0,
    animationDurationUpdate: 0,
  };
}

export function useECharts(
  containerRef: RefObject<HTMLDivElement | null>,
  option: EChartsOption | null,
  { enabled = true }: UseEChartsOptions = {},
): void {
  const chartRef = useRef<ReturnType<typeof echarts.init> | null>(null);
  const optionRef = useRef<EChartsOption | null>(option);

  optionRef.current = option;

  useEffect(() => {
    const container = containerRef.current;

    if (!enabled || container === null) {
      return undefined;
    }

    const chart = echarts.init(container, chartThemeName, {
      renderer: "canvas",
    });
    chartRef.current = chart;

    const resize = () => {
      chart.resize();
    };

    const resizeObserver =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(resize);

    resizeObserver?.observe(container);
    window.addEventListener("resize", resize);

    const mediaQuery = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    );
    const handleMotionChange = () => {
      if (optionRef.current !== null) {
        chart.setOption(optionForMotionPreference(optionRef.current), {
          notMerge: true,
          lazyUpdate: false,
        });
      }
    };

    mediaQuery?.addEventListener?.("change", handleMotionChange);

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", resize);
      mediaQuery?.removeEventListener?.("change", handleMotionChange);
      chart.dispose();
      chartRef.current = null;
    };
  }, [containerRef, enabled]);

  useEffect(() => {
    const chart = chartRef.current;

    if (!enabled || chart === null || option === null) {
      return;
    }

    chart.setOption(optionForMotionPreference(option), {
      notMerge: true,
      lazyUpdate: false,
    });
  }, [enabled, option]);
}
