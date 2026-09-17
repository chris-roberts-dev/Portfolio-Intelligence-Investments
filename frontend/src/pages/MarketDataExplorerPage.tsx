import {
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";

import { ApiError } from "../api/client";
import { MarketCandlestickChart } from "../components/charts/MarketCandlestickChart";
import { MarketPriceChart } from "../components/charts/MarketPriceChart";
import { Skeleton } from "../components/ui/Skeleton";
import { StatePanel } from "../components/ui/StatePanel";
import {
  formatDateTime,
  humanizeCode,
} from "../features/dashboard/formatting";
import { parseMarketSymbols } from "../features/marketData/marketDataTransforms";
import { useMarketBarQuery } from "../hooks/useMarketData";
import { DashboardShell } from "../layouts/DashboardShell";
import type {
  MarketBarQueryRequest,
  MarketBarStatus,
  MarketBarSymbolResult,
} from "../types/marketData";

function formatLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function defaultDateRange(now = new Date()): {
  start: string;
  end: string;
} {
  const start = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() - 30,
  );

  const end = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + 1,
  );

  return {
    start: formatLocalIsoDate(start),
    end: formatLocalIsoDate(end),
  };
}

function sameRequest(
  left: MarketBarQueryRequest | null,
  right: MarketBarQueryRequest,
): boolean {
  return (
    left !== null &&
    left.start === right.start &&
    left.end === right.end &&
    left.interval === right.interval &&
    (left.provider ?? null) ===
      (right.provider ?? null) &&
    left.symbols.length === right.symbols.length &&
    left.symbols.every(
      (symbol, index) =>
        symbol === right.symbols[index],
    )
  );
}

function statusPresentation(
  status: MarketBarStatus,
): {
  label: string;
  icon: string;
  className: string;
} {
  switch (status) {
    case "SUCCEEDED":
      return {
        label: "Succeeded",
        icon: "✓",
        className:
          "border-emerald-200 bg-emerald-50 text-emerald-800",
      };

    case "NOT_FOUND":
      return {
        label: "Not found",
        icon: "—",
        className:
          "border-slate-200 bg-slate-50 text-slate-700",
      };

    case "NO_DATA":
      return {
        label: "No data",
        icon: "—",
        className:
          "border-amber-200 bg-amber-50 text-amber-900",
      };

    case "FAILED":
      return {
        label: "Failed",
        icon: "!",
        className:
          "border-rose-200 bg-rose-50 text-rose-900",
      };
  }
}

function validationMessages(
  error: ApiError,
): string[] {
  if (
    error.payload === null ||
    typeof error.payload !== "object" ||
    !("errors" in error.payload)
  ) {
    return [];
  }

  const errors = error.payload.errors;

  if (
    errors === null ||
    typeof errors !== "object"
  ) {
    return [];
  }

  return Object.entries(errors).flatMap(
    ([field, value]) => {
      if (!Array.isArray(value)) {
        return [];
      }

      return value
        .filter(
          (item): item is string =>
            typeof item === "string",
        )
        .map(
          (item) =>
            `${humanizeCode(field) ?? field}: ${item}`,
        );
    },
  );
}

function queryErrorTitle(
  error: Error,
): string {
  if (!(error instanceof ApiError)) {
    return "Market data could not load";
  }

  switch (error.status) {
    case 400:
      return "Market-data request is invalid";
    case 403:
      return "Market-data provider access denied";
    case 429:
      return "Market-data request limit reached";
    case 503:
      return "Market-data provider unavailable";
    default:
      return "Market data could not load";
  }
}

function MarketDataSkeleton() {
  return (
    <div aria-label="Loading market data">
      <Skeleton className="h-32 w-full rounded-3xl" />
      <Skeleton className="mt-5 h-80 w-full rounded-3xl" />
    </div>
  );
}

function SymbolResultCard({
  result,
  selected,
  onSelect,
}: {
  result: MarketBarSymbolResult;
  selected: boolean;
  onSelect: () => void;
}) {
  const presentation =
    statusPresentation(result.status);

  const content = (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-950">
            {result.symbol}
          </h3>

          <p className="mt-1 text-xs text-slate-500">
            {result.asset_id ??
              "No resolved asset"}
          </p>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${presentation.className}`}
        >
          <span aria-hidden="true">
            {presentation.icon}
          </span>
          {presentation.label}
        </span>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        {result.bars.length} daily bar
        {result.bars.length === 1
          ? ""
          : "s"}
      </p>

      {result.warnings.length > 0 ? (
        <ul className="mt-3 space-y-1 text-xs leading-5 text-amber-900">
          {result.warnings.map(
            (warning) => (
              <li key={warning}>
                {warning}
              </li>
            ),
          )}
        </ul>
      ) : null}
    </>
  );

  if (result.status !== "SUCCEEDED") {
    return (
      <li className="rounded-2xl border border-slate-200 bg-white p-4">
        {content}
      </li>
    );
  }

  return (
    <li>
      <button
        type="button"
        aria-label={`${result.symbol} — View candlestick detail`}
        aria-controls="market-candlestick-detail"
        aria-pressed={selected}
        onClick={onSelect}
        className={`w-full rounded-2xl border bg-white p-4 text-left shadow-sm outline-none transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
          selected
            ? "border-blue-300 ring-1 ring-blue-200"
            : "border-slate-200 hover:border-blue-200"
        }`}
      >
        {content}

        <span className="mt-3 inline-block text-xs font-semibold text-blue-700">
          View candlestick detail →
        </span>
      </button>
    </li>
  );
}

export function MarketDataExplorerPage() {
  const defaults = defaultDateRange();

  const [symbolInput, setSymbolInput] =
    useState("");

  const [start, setStart] = useState(
    defaults.start,
  );

  const [end, setEnd] = useState(
    defaults.end,
  );

  const [
    submittedRequest,
    setSubmittedRequest,
  ] =
    useState<MarketBarQueryRequest | null>(
      null,
    );

  const [
    selectedSymbol,
    setSelectedSymbol,
  ] = useState<string | null>(null);

  const [formError, setFormError] =
    useState<string | null>(null);

  const detailSectionRef =
    useRef<HTMLElement | null>(null);

  const normalizedSymbols =
    parseMarketSymbols(symbolInput);

  const marketQuery =
    useMarketBarQuery(submittedRequest);

  const result = marketQuery.data;

  /*
   * These derived arrays intentionally retain the same reference while the
   * TanStack Query result is unchanged. Changing selectedSymbol therefore does
   * not force MarketPriceChart to rebuild its 14+ series.
   */
  const successfulResults = useMemo(
    () =>
      result?.results.filter(
        (symbolResult) =>
          symbolResult.status ===
          "SUCCEEDED",
      ) ?? [],
    [result?.results],
  );

  const unavailableResults = useMemo(
    () =>
      result?.results.filter(
        (symbolResult) =>
          symbolResult.status !==
          "SUCCEEDED",
      ) ?? [],
    [result?.results],
  );

  const detailResult = useMemo(
    () =>
      successfulResults.find(
        (symbolResult) =>
          symbolResult.symbol ===
          selectedSymbol,
      ) ??
      successfulResults[0] ??
      null,
    [
      successfulResults,
      selectedSymbol,
    ],
  );

  const header = (
    <div className="mx-auto flex min-h-20 w-full max-w-[1600px] items-center px-4 py-3 sm:px-6 lg:px-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
          Provider-neutral market data
        </p>

        <h1 className="mt-1 text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl">
          Market Data Explorer
        </h1>
      </div>
    </div>
  );

  function selectDetailSymbol(
    symbol: string,
  ) {
    setSelectedSymbol(symbol);

    const prefersReducedMotion =
      window.matchMedia?.(
        "(prefers-reduced-motion: reduce)",
      ).matches ?? false;

    detailSectionRef.current?.scrollIntoView(
      {
        behavior:
          prefersReducedMotion
            ? "auto"
            : "smooth",
        block: "start",
      },
    );
  }

  function submitQuery(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const symbols = normalizedSymbols;

    if (symbols.length === 0) {
      setFormError(
        "Enter at least one ticker symbol.",
      );
      return;
    }

    if (
      !start ||
      !end ||
      start >= end
    ) {
      setFormError(
        "Choose a start date earlier than the exclusive end date.",
      );
      return;
    }

    const nextRequest: MarketBarQueryRequest =
      {
        symbols,
        start,
        end,
        interval: "1d",
      };

    setFormError(null);
    setSelectedSymbol(null);

    /*
     * Re-submitting exactly the same form is an intentional user refresh.
     * Automatic focus/mount/reconnect refreshes are disabled in the query
     * hook, but an explicit Query click is allowed to request fresh data.
     */
    if (
      sameRequest(
        submittedRequest,
        nextRequest,
      )
    ) {
      void marketQuery.refetch();
      return;
    }

    setSubmittedRequest(nextRequest);
  }

  const apiError =
    marketQuery.error instanceof ApiError
      ? marketQuery.error
      : null;

  const apiValidationMessages =
    apiError?.status === 400
      ? validationMessages(apiError)
      : [];

  return (
    <DashboardShell header={header}>
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="max-w-3xl">
          <h2 className="text-lg font-semibold tracking-tight text-slate-950">
            Query daily market bars
          </h2>

          <p className="mt-1 text-sm leading-6 text-slate-600">
            Enter one or more canonical ticker
            symbols. Dates use an inclusive
            start and exclusive end. Results
            remain provider-neutral and no
            missing price is filled or
            interpolated in the browser.
          </p>
        </div>

        <form
          className="mt-5 grid gap-4 lg:grid-cols-12"
          onSubmit={submitQuery}
        >
          <div className="lg:col-span-6">
            <label
              htmlFor="market-symbols"
              className="text-xs font-semibold text-slate-700"
            >
              Ticker symbols
            </label>

            <textarea
              id="market-symbols"
              value={symbolInput}
              onChange={(event) =>
                setSymbolInput(
                  event.target.value,
                )
              }
              rows={3}
              placeholder={"AAPL, MSFT\nSPY"}
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm uppercase text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              aria-describedby="ticker-help"
            />

            <span
              id="ticker-help"
              className="mt-1 block text-xs text-slate-500"
            >
              Commas, spaces, and new lines
              are accepted. Duplicates are
              removed while preserving first
              occurrence.
            </span>

            {normalizedSymbols.length >
            0 ? (
              <div
                className="mt-2 flex flex-wrap gap-1.5"
                aria-label="Normalized symbols"
              >
                {normalizedSymbols.map(
                  (symbol) => (
                    <span
                      key={symbol}
                      className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-800"
                    >
                      {symbol}
                    </span>
                  ),
                )}
              </div>
            ) : null}
          </div>

          <div className="lg:col-span-2">
            <label
              htmlFor="market-start"
              className="text-xs font-semibold text-slate-700"
            >
              Start
            </label>

            <input
              id="market-start"
              type="date"
              value={start}
              onChange={(event) =>
                setStart(
                  event.target.value,
                )
              }
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </div>

          <div className="lg:col-span-2">
            <label
              htmlFor="market-end"
              className="text-xs font-semibold text-slate-700"
            >
              End (exclusive)
            </label>

            <input
              id="market-end"
              type="date"
              value={end}
              onChange={(event) =>
                setEnd(
                  event.target.value,
                )
              }
              className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            />
          </div>

          <div className="flex items-start lg:col-span-2 lg:pt-6">
            <button
              type="submit"
              className="w-full rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none transition hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
            >
              Query
            </button>
          </div>

          <div className="lg:col-span-12">
            <p className="text-xs text-slate-500">
              Interval:{" "}
              <strong>Daily (1d)</strong> ·
              Provider: server-configured
              default
            </p>

            {formError ? (
              <p
                role="alert"
                className="mt-2 text-sm font-medium text-rose-700"
              >
                {formError}
              </p>
            ) : null}
          </div>
        </form>
      </section>

      {submittedRequest === null ? (
        <div className="mt-5">
          <StatePanel
            title="Submit a market-data query"
            message="Results will appear here after you explicitly submit ticker symbols and a bounded date range."
          />
        </div>
      ) : marketQuery.isPending &&
        result === undefined ? (
        <div className="mt-5">
          <MarketDataSkeleton />
        </div>
      ) : marketQuery.error instanceof
          Error &&
        result === undefined ? (
        <div className="mt-5">
          <StatePanel
            title={queryErrorTitle(
              marketQuery.error,
            )}
            message={
              marketQuery.error.message
            }
            tone="error"
            action={
              <button
                type="button"
                onClick={() =>
                  void marketQuery.refetch()
                }
                className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
              >
                Retry
              </button>
            }
          />

          {apiValidationMessages.length >
          0 ? (
            <ul className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
              {apiValidationMessages.map(
                (message) => (
                  <li key={message}>
                    {message}
                  </li>
                ),
              )}
            </ul>
          ) : null}
        </div>
      ) : result === undefined ? null : (
        <div className="mt-5 space-y-5">
          {marketQuery.error instanceof
          Error ? (
            <div
              className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
              role="status"
            >
              Refresh failed. Showing the most
              recent successful market-data
              result.
            </div>
          ) : null}

          {marketQuery.isFetching ? (
            <div
              className="inline-flex rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800"
              role="status"
              aria-live="polite"
            >
              Refreshing market data…
            </div>
          ) : null}

          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                  Query provenance
                </p>

                <h2 className="mt-1 text-lg font-semibold text-slate-950">
                  {result.meta.provider} ·{" "}
                  {result.meta.interval}
                </h2>
              </div>

              {successfulResults.length >
                0 &&
              unavailableResults.length >
                0 ? (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900">
                  Partial success
                </span>
              ) : unavailableResults.length ===
                0 ? (
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                  Query complete
                </span>
              ) : (
                <span className="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-900">
                  No successful symbols
                </span>
              )}
            </div>

            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
              <div>
                <dt className="text-xs text-slate-500">
                  Requested period
                </dt>

                <dd className="mt-1 font-medium text-slate-900">
                  {result.meta.start} to{" "}
                  {result.meta.end} (end
                  exclusive)
                </dd>
              </div>

              <div>
                <dt className="text-xs text-slate-500">
                  Retrieved
                </dt>

                <dd className="mt-1 font-medium text-slate-900">
                  {formatDateTime(
                    result.meta
                      .retrieved_at,
                  )}
                </dd>
              </div>

              <div>
                <dt className="text-xs text-slate-500">
                  Symbols
                </dt>

                <dd className="mt-1 font-medium tabular-nums text-slate-900">
                  {result.results.length}
                </dd>
              </div>

              <div>
                <dt className="text-xs text-slate-500">
                  Canonical bars
                </dt>

                <dd className="mt-1 font-medium tabular-nums text-slate-900">
                  {result.row_count}
                </dd>
              </div>

              <div>
                <dt className="text-xs text-slate-500">
                  Price view
                </dt>

                <dd className="mt-1 font-medium text-slate-900">
                  Raw close / OHLC · no
                  normalization or fill
                </dd>
              </div>
            </dl>
          </section>

          {result.results.length === 0 ? (
            <StatePanel
              title="No market-data results"
              message="The provider completed the request without returning symbol results."
            />
          ) : (
            <section
              className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              aria-labelledby="symbol-status-heading"
            >
              <h2
                id="symbol-status-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Symbol status
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                Every requested symbol remains
                visible, including failures and
                no-data outcomes.
              </p>

              <ul className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {result.results.map(
                  (symbolResult) => (
                    <SymbolResultCard
                      key={
                        symbolResult.symbol
                      }
                      result={
                        symbolResult
                      }
                      selected={
                        detailResult?.symbol ===
                        symbolResult.symbol
                      }
                      onSelect={() =>
                        selectDetailSymbol(
                          symbolResult.symbol,
                        )
                      }
                    />
                  ),
                )}
              </ul>
            </section>
          )}

          {detailResult ? (
            <section
              ref={detailSectionRef}
              id="market-candlestick-detail"
              className="scroll-mt-28 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              aria-labelledby="candlestick-heading"
            >
              <h2
                id="candlestick-heading"
                className="text-lg font-semibold text-slate-950"
              >
                {detailResult.symbol}{" "}
                candlestick detail
              </h2>

              <p className="mt-1 text-sm leading-6 text-slate-500">
                Daily OHLC values are plotted
                in canonical ECharts order
                [open, close, low, high] with
                volume aligned to the same
                dates.
              </p>

              <div className="mt-4">
                <MarketCandlestickChart
                  result={detailResult}
                />
              </div>
            </section>
          ) : null}

          {successfulResults.length > 0 ? (
            <section
              className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
              aria-labelledby="raw-price-heading"
            >
              <h2
                id="raw-price-heading"
                className="text-lg font-semibold text-slate-950"
              >
                Raw close price history
              </h2>

              <p className="mt-1 text-sm leading-6 text-slate-500">
                Provider-returned daily close
                price levels. This view is not
                normalized and does not fill or
                connect missing values.
              </p>

              <div className="mt-4">
                <MarketPriceChart
                  results={
                    successfulResults
                  }
                />
              </div>
            </section>
          ) : null}
        </div>
      )}
    </DashboardShell>
  );
}