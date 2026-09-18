import { resolveOverviewDateRange } from "./overviewRange";

describe("resolveOverviewDateRange", () => {
  it("uses the supplied ledger inception date for Max", () => {
    expect(
      resolveOverviewDateRange(
        "MAX",
        "2020-01-02T14:00:00Z",
        new Date(2026, 8, 18, 12, 0, 0),
      ),
    ).toEqual({
      start: "2020-01-02",
      end: "2026-09-19",
    });
  });
});
