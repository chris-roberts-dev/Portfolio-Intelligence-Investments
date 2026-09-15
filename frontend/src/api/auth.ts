import { apiGet, apiPost } from "./client";

export interface AuthenticatedUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface AuthSessionResult {
  authenticated: boolean;
  user: AuthenticatedUser | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export function fetchAuthSession(signal?: AbortSignal): Promise<AuthSessionResult> {
  return apiGet<AuthSessionResult>("/api/v1/auth/session/", { signal });
}

export function loginWithPassword(
  request: LoginRequest,
  signal?: AbortSignal,
): Promise<AuthSessionResult> {
  return apiPost<AuthSessionResult, LoginRequest>(
    "/api/v1/auth/login/",
    request,
    { signal },
  );
}

export function logoutSession(signal?: AbortSignal): Promise<AuthSessionResult> {
  return apiPost<AuthSessionResult, Record<string, never>>(
    "/api/v1/auth/logout/",
    {},
    { signal },
  );
}
