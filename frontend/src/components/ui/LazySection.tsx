import {
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
  type ReactNode,
} from "react";

interface LazySectionProps extends PropsWithChildren {
  fallback: ReactNode;
  rootMargin?: string;
}

export function LazySection({
  fallback,
  rootMargin = "320px 0px",
  children,
}: LazySectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(
    () => typeof IntersectionObserver === "undefined",
  );

  useEffect(() => {
    if (isVisible || typeof IntersectionObserver === "undefined") {
      return undefined;
    }

    const container = containerRef.current;

    if (container === null) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );

    observer.observe(container);

    return () => observer.disconnect();
  }, [isVisible, rootMargin]);

  return (
    <div ref={containerRef}>
      {isVisible ? children : fallback}
    </div>
  );
}
