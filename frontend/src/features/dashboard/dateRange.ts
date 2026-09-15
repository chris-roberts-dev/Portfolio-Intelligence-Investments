export type DashboardRange = "1W" | "1M" | "3M" | "6M" | "YTD" | "1Y" | "ALL";

export const DASHBOARD_RANGES: readonly DashboardRange[] = [
  "1W",
  "1M",
  "3M",
  "6M",
  "YTD",
  "1Y",
  "ALL",
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

export function formatLocalIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function resolveDashboardDateRange(
  range: DashboardRange,
  portfolioCreatedAt: string,
  now: Date = new Date(),
): { start: string; end: string } {
  const today = startOfLocalDay(now);
  const endExclusive = addDays(today, 1);
  let start: Date;

  switch (range) {
    case "1W":
      start = addDays(today, -7);
      break;
    case "1M":
      start = addMonths(today, -1);
      break;
    case "3M":
      start = addMonths(today, -3);
      break;
    case "6M":
      start = addMonths(today, -6);
      break;
    case "YTD":
      start = new Date(today.getFullYear(), 0, 1);
      break;
    case "1Y":
      start = addYears(today, -1);
      break;
    case "ALL": {
      const [createdDate] = portfolioCreatedAt.split("T");
      return {
        start: createdDate || formatLocalIsoDate(addYears(today, -1)),
        end: formatLocalIsoDate(endExclusive),
      };
    }
  }

  return {
    start: formatLocalIsoDate(start),
    end: formatLocalIsoDate(endExclusive),
  };
}
