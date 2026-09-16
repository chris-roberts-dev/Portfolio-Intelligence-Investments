export const chartTheme = {
  primary: "#2563eb",
  benchmark: "#64748b",
  gridline: "#e2e8f0",
  axisText: "#64748b",
  tooltipBackground: "#0f172a",
  tooltipText: "#f8fafc",
} as const;

export const chartThemeName = "portfolio-intelligence";

export const echartsTheme = {
  color: [
    chartTheme.primary,
    "#0f766e",
    "#7c3aed",
    "#d97706",
    chartTheme.benchmark,
  ],
  textStyle: {
    color: chartTheme.axisText,
  },
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: chartTheme.gridline,
      },
    },
    axisLabel: {
      color: chartTheme.axisText,
    },
  },
  valueAxis: {
    axisLine: {
      lineStyle: {
        color: chartTheme.gridline,
      },
    },
    axisLabel: {
      color: chartTheme.axisText,
    },
    splitLine: {
      lineStyle: {
        color: chartTheme.gridline,
      },
    },
  },
  tooltip: {
    backgroundColor: chartTheme.tooltipBackground,
    borderWidth: 0,
    textStyle: {
      color: chartTheme.tooltipText,
    },
  },
};
