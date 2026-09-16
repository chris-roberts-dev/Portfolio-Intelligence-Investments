import { ApiError } from "../../api/client";

export function apiFieldErrors(error: unknown): Record<string, string[]> {
  if (!(error instanceof ApiError)) {
    return {};
  }

  const payload = error.payload;
  if (payload === null || typeof payload !== "object") {
    return {};
  }

  const errors = (payload as { errors?: unknown }).errors;
  if (errors === null || typeof errors !== "object") {
    return {};
  }

  const normalized: Record<string, string[]> = {};

  for (const [field, value] of Object.entries(errors)) {
    if (Array.isArray(value)) {
      normalized[field] = value.map((item) => String(item));
    } else if (value !== undefined && value !== null) {
      normalized[field] = [String(value)];
    }
  }

  return normalized;
}

export function firstFieldError(
  errors: Record<string, string[]>,
  field: string,
): string | null {
  return errors[field]?.[0] ?? null;
}
