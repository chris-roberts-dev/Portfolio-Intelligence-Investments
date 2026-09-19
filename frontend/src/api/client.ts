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

function csrfTokenFromCookie(): string | null {
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("csrftoken="));

  if (!cookie) {
    return null;
  }

  const value = cookie.slice("csrftoken=".length);
  return value ? decodeURIComponent(value) : null;
}

function firstValidationMessage(value: unknown): string | null {
  if (typeof value === "string") {
    const message = value.trim();
    return message.length > 0 ? message : null;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstValidationMessage(item);
      if (message !== null) {
        return message;
      }
    }
    return null;
  }

  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const nonFieldMessage = firstValidationMessage(record.non_field_errors);
    if (nonFieldMessage !== null) {
      return nonFieldMessage;
    }

    for (const nested of Object.values(record)) {
      const message = firstValidationMessage(nested);
      if (message !== null) {
        return message;
      }
    }
  }

  return null;
}

function errorMessage(payload: ApiErrorPayload, response: Response): string {
  if (typeof payload.detail === "string" && payload.detail.length > 0) {
    return payload.detail;
  }

  const validationMessage = firstValidationMessage(payload.errors);
  if (validationMessage !== null) {
    return validationMessage;
  }

  if (typeof payload.code === "string" && payload.code.length > 0) {
    return payload.code.replaceAll("_", " ").toLowerCase();
  }

  return `Request failed with status ${response.status}.`;
}

async function parseResponse<T>(response: Response): Promise<T> {
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

  return parseResponse<T>(response);
}

export async function apiPost<T, TBody extends object>(
  path: string,
  body: TBody,
  options: { signal?: AbortSignal } = {},
): Promise<T> {
  const csrfToken = csrfTokenFromCookie();
  const headers = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });

  if (csrfToken !== null) {
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify(body),
    signal: options.signal,
  });

  return parseResponse<T>(response);
}

export async function apiPatch<T, TBody extends object>(
  path: string,
  body: TBody,
  options: { signal?: AbortSignal } = {},
): Promise<T> {
  const csrfToken = csrfTokenFromCookie();
  const headers = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });

  if (csrfToken !== null) {
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "PATCH",
    credentials: "include",
    headers,
    body: JSON.stringify(body),
    signal: options.signal,
  });

  return parseResponse<T>(response);
}

export async function apiDelete(
  path: string,
  options: { signal?: AbortSignal } = {},
): Promise<void> {
  const csrfToken = csrfTokenFromCookie();
  const headers = new Headers({
    Accept: "application/json",
  });

  if (csrfToken !== null) {
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "DELETE",
    credentials: "include",
    headers,
    signal: options.signal,
  });

  if (response.ok && response.status === 204) {
    return;
  }

  await parseResponse<unknown>(response);
}
