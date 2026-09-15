import { act, render, screen } from "@testing-library/react";

import { LazySection } from "./LazySection";

describe("LazySection", () => {
  it("defers lower-page content until it approaches the viewport", () => {
    let callback: IntersectionObserverCallback | null = null;
    const observe = vi.fn();
    const disconnect = vi.fn();

    class MockIntersectionObserver {
      root = null;
      rootMargin = "320px 0px";
      thresholds = [0];

      constructor(nextCallback: IntersectionObserverCallback) {
        callback = nextCallback;
      }

      observe = observe;
      unobserve = vi.fn();
      disconnect = disconnect;
      takeRecords = vi.fn(() => []);
    }

    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);

    render(
      <LazySection fallback={<div>Deferred holdings</div>}>
        <div>Loaded holdings</div>
      </LazySection>,
    );

    expect(screen.getByText("Deferred holdings")).toBeInTheDocument();
    expect(screen.queryByText("Loaded holdings")).not.toBeInTheDocument();
    expect(observe).toHaveBeenCalledTimes(1);

    act(() => {
      callback?.(
        [
          {
            isIntersecting: true,
          } as IntersectionObserverEntry,
        ],
        {} as IntersectionObserver,
      );
    });

    expect(screen.getByText("Loaded holdings")).toBeInTheDocument();
    expect(disconnect).toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});
