export type OverviewRange = "1M" | "3M" | "YTD" | "1Y" | "3Y" | "5Y" | "MAX";

export const OVERVIEW_RANGES: readonly OverviewRange[] = [
  "1M",
  "3M",
  "YTD",
  "1Y",
  "3Y",
  "5Y",
  "MAX",
];

function startOfLocalDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function addDays(value: Date, days: number): Date {
  const result = new Date(value);
  result.setDate(result.getDate() + days);
  return result;
}

function addMonths(value: Date, months: number): Date {
  const result = new Date(value);
  result.setMonth(result.getMonth() + months);
  return result;
}

function addYears(value: Date, years: number): Date {
  const result = new Date(value);
  result.setFullYear(result.getFullYear() + years);
  return result;
}

function formatLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function isOverviewRange(value: string | null): value is OverviewRange {
  return value !== null && OVERVIEW_RANGES.includes(value as OverviewRange);
}

export function resolveOverviewDateRange(
  range: OverviewRange,
  portfolioInceptionAt: string,
  now: Date = new Date(),
): { start: string; end: string } {
  const today = startOfLocalDay(now);
  const end = formatLocalIsoDate(addDays(today, 1));

  if (range === "MAX") {
    const [inceptionDate] = portfolioInceptionAt.split("T");
    return {
      start: inceptionDate || formatLocalIsoDate(addYears(today, -1)),
      end,
    };
  }

  let start: Date;

  switch (range) {
    case "1M":
      start = addMonths(today, -1);
      break;
    case "3M":
      start = addMonths(today, -3);
      break;
    case "YTD":
      start = new Date(today.getFullYear(), 0, 1);
      break;
    case "1Y":
      start = addYears(today, -1);
      break;
    case "3Y":
      start = addYears(today, -3);
      break;
    case "5Y":
      start = addYears(today, -5);
      break;
  }

  return {
    start: formatLocalIsoDate(start),
    end,
  };
}