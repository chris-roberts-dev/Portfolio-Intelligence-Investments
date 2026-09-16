import type { EChartsOption } from "echarts";
import { render } from "@testing-library/react";
import * as echarts from "echarts/core";
import { useMemo, useRef } from "react";

import { useECharts } from "./useECharts";

const setOption = vi.fn();
const resize = vi.fn();
const dispose = vi.fn();

vi.mock("echarts/core", () => ({
  registerTheme: vi.fn(),
  init: vi.fn(() => ({
    setOption,
    resize,
    dispose,
  })),
}));

let resizeObserverCallback: ResizeObserverCallback | null = null;
const observe = vi.fn();
const disconnect = vi.fn();

class TestResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    resizeObserverCallback = callback;
  }

  observe = observe;
  unobserve = vi.fn();
  disconnect = disconnect;
}

function Harness({ value }: { value: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const option = useMemo<EChartsOption>(
    () => ({
      animation: true,
      series: [{ type: "line", data: [value] }],
    }),
    [value],
  );

  useECharts(ref, option);

  return <div ref={ref} data-testid="chart" />;
}

describe("useECharts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resizeObserverCallback = null;
    vi.stubGlobal("ResizeObserver", TestResizeObserver);
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: false,
        media: "(prefers-reduced-motion: reduce)",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("initializes once, updates options, resizes from ResizeObserver, and disposes", () => {
    const view = render(<Harness value={1} />);

    expect(echarts.init).toHaveBeenCalledTimes(1);
    expect(echarts.init).toHaveBeenCalledWith(
      view.getByTestId("chart"),
      "portfolio-intelligence",
      { renderer: "canvas" },
    );
    expect(observe).toHaveBeenCalledWith(
      view.getByTestId("chart"),
    );
    expect(setOption).toHaveBeenCalledTimes(1);

    view.rerender(<Harness value={2} />);

    expect(echarts.init).toHaveBeenCalledTimes(1);
    expect(setOption).toHaveBeenCalledTimes(2);

    resizeObserverCallback?.([], {} as ResizeObserver);
    expect(resize).toHaveBeenCalledTimes(1);

    view.unmount();

    expect(disconnect).toHaveBeenCalledTimes(1);
    expect(dispose).toHaveBeenCalledTimes(1);
  });

  it("forces animation off when reduced motion is requested", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({
        matches: true,
        media: "(prefers-reduced-motion: reduce)",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );

    render(<Harness value={1} />);

    expect(setOption).toHaveBeenCalledWith(
      expect.objectContaining({
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
      }),
      expect.objectContaining({
        notMerge: true,
        lazyUpdate: false,
      }),
    );
  });
});
