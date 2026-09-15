import { fetchDashboardSnapshot } from "./portfolios";

describe("fetchDashboardSnapshot", () => {
  it("requests the canonical owner-scoped snapshot with explicit range inputs", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          snapshot: {
            snapshot_id: "00000000-0000-0000-0000-000000000001",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchDashboardSnapshot({
      portfolioId: "00000000-0000-0000-0000-000000000002",
      start: "2026-09-01",
      end: "2026-09-16",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/portfolios/00000000-0000-0000-0000-000000000002/dashboard/?start=2026-09-01&end=2026-09-16",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );
  });
});
