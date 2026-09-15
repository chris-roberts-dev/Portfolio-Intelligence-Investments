interface ApiErrorPayload {
  code?: unknown;
  detail?: unknown;
  errors?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly payload: unknown;

  constructor(
    message: string,
    options: { status: number; code: string | null; payload: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.payload = options.payload;
  }
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();

  if (!configured) {
    return "";
  }

  return configured.endsWith("/") ? configured.slice(0, -1) : configured;
}

function errorMessage(payload: ApiErrorPayload, response: Response): string {
  if (typeof payload.detail === "string" && payload.detail.length > 0) {
    return payload.detail;
  }

  if (typeof payload.code === "string" && payload.code.length > 0) {
    return payload.code.replaceAll("_", " ").toLowerCase();
  }

  return `Request failed with status ${response.status}.`;
}

export async function apiGet<T>(
  path: string,
  options: { signal?: AbortSignal } = {},
): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
    signal: options.signal,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const errorPayload =
      payload !== null && typeof payload === "object"
        ? (payload as ApiErrorPayload)
        : {};

    throw new ApiError(errorMessage(errorPayload, response), {
      status: response.status,
      code: typeof errorPayload.code === "string" ? errorPayload.code : null,
      payload,
    });
  }

  return payload as T;
}
