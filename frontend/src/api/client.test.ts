import { apiGet } from "./client";

function jsonResponse(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client validation errors", () => {
  it("surfaces DRF non_field_errors before the generic error code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          {
            code: "VALIDATION_ERROR",
            errors: {
              non_field_errors: [
                "Historical comparison requires positive investable value at the requested period start.",
              ],
            },
          },
          400,
        ),
      ),
    );

    await expect(apiGet("/api/v1/example/")).rejects.toMatchObject({
      status: 400,
      code: "VALIDATION_ERROR",
      message:
        "Historical comparison requires positive investable value at the requested period start.",
    });
  });

  it("surfaces field validation messages when non_field_errors are absent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          {
            code: "VALIDATION_ERROR",
            errors: {
              period_end: ["period_end must be later than period_start."],
            },
          },
          400,
        ),
      ),
    );

    await expect(apiGet("/api/v1/example/")).rejects.toMatchObject({
      status: 400,
      code: "VALIDATION_ERROR",
      message: "period_end must be later than period_start.",
    });
  });
});
