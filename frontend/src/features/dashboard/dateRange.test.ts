import { isDashboardRange, resolveDashboardDateRange } from "./dateRange";

describe("resolveDashboardDateRange", () => {
  const now = new Date(2026, 8, 18, 12, 0, 0);

  it("uses an exclusive next-day end date", () => {
    expect(
      resolveDashboardDateRange("1W", "2025-01-01T00:00:00Z", null, now),
    ).toEqual({
      start: "2026-09-11",
      end: "2026-09-19",
    });
  });

  it("uses earliest ledger inception for the All range", () => {
    expect(
      resolveDashboardDateRange(
        "ALL",
        "2026-09-18T13:00:00Z",
        "2020-01-02T14:00:00Z",
        now,
      ),
    ).toEqual({
      start: "2020-01-02",
      end: "2026-09-19",
    });
  });

  it("falls back to portfolio creation when no ledger transaction exists", () => {
    expect(
      resolveDashboardDateRange("ALL", "2025-01-02T15:00:00Z", null, now),
    ).toEqual({
      start: "2025-01-02",
      end: "2026-09-19",
    });
  });

  it("supports month-to-date and quarter-to-date report presets", () => {
    expect(
      resolveDashboardDateRange("MTD", "2020-01-01T00:00:00Z", null, now),
    ).toEqual({ start: "2026-09-01", end: "2026-09-19" });
    expect(
      resolveDashboardDateRange("QTD", "2020-01-01T00:00:00Z", null, now),
    ).toEqual({ start: "2026-07-01", end: "2026-09-19" });
  });

  it("supports report-friendly three and five year ranges", () => {
    expect(
      resolveDashboardDateRange("3Y", "2020-01-01T00:00:00Z", null, now),
    ).toEqual({ start: "2023-09-18", end: "2026-09-19" });
    expect(
      resolveDashboardDateRange("5Y", "2020-01-01T00:00:00Z", null, now),
    ).toEqual({ start: "2021-09-18", end: "2026-09-19" });
  });
});


describe("isDashboardRange", () => {
  it("accepts supported report and dashboard ranges only", () => {
    expect(isDashboardRange("3Y")).toBe(true);
    expect(isDashboardRange("ALL")).toBe(true);
    expect(isDashboardRange("MAX")).toBe(false);
    expect(isDashboardRange(null)).toBe(false);
  });
});
