import {
  fetchAuthSession,
  loginWithPassword,
  logoutSession,
} from "./auth";

beforeEach(() => {
  document.cookie = "csrftoken=test-csrf-token; path=/";
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("session authentication API", () => {
  it("boots the current session with credentials included", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({
          authenticated: false,
          user: null,
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await fetchAuthSession();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/session/",
      expect.objectContaining({
        method: "GET",
        credentials: "include",
      }),
    );
  });

  it("sends JSON credentials and the CSRF cookie on login", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({
          authenticated: true,
          user: {
            id: "00000000-0000-0000-0000-000000000001",
            email: "owner@example.com",
            first_name: "Portfolio",
            last_name: "Owner",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await loginWithPassword({
      email: "owner@example.com",
      password: "secret-password",
    });

    const [, request] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers(request?.headers);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/auth/login/");
    expect(request?.method).toBe("POST");
    expect(request?.credentials).toBe("include");
    expect(headers.get("X-CSRFToken")).toBe("test-csrf-token");
    expect(request?.body).toBe(
      JSON.stringify({
        email: "owner@example.com",
        password: "secret-password",
      }),
    );
  });

  it("sends the current CSRF token when logging out", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(
        JSON.stringify({
          authenticated: false,
          user: null,
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await logoutSession();

    const [, request] = fetchMock.mock.calls[0] ?? [];
    const headers = new Headers(request?.headers);

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/auth/logout/");
    expect(request?.method).toBe("POST");
    expect(headers.get("X-CSRFToken")).toBe("test-csrf-token");
  });
});
