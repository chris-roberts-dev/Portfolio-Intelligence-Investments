import { resolveDashboardDateRange } from "./dateRange";

describe("resolveDashboardDateRange", () => {
  const now = new Date(2026, 8, 15, 12, 0, 0);

  it("uses an exclusive next-day end date", () => {
    expect(resolveDashboardDateRange("1W", "2025-01-01T00:00:00Z", now)).toEqual({
      start: "2026-09-08",
      end: "2026-09-16",
    });
  });

  it("uses portfolio creation date for the All range", () => {
    expect(resolveDashboardDateRange("ALL", "2025-01-02T15:00:00Z", now)).toEqual({
      start: "2025-01-02",
      end: "2026-09-16",
    });
  });
});
