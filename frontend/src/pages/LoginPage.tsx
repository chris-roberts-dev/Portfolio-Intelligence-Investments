import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import { useLogin, useSession } from "../hooks/useAuth";

interface LoginLocationState {
  from?: unknown;
}

function safeReturnTo(state: unknown): string {
  if (state === null || typeof state !== "object") {
    return "/";
  }

  const from = (state as LoginLocationState).from;
  if (
    typeof from !== "string" ||
    !from.startsWith("/") ||
    from.startsWith("//") ||
    from.startsWith("/login")
  ) {
    return "/";
  }

  return from;
}

export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const sessionQuery = useSession();
  const loginMutation = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const returnTo = safeReturnTo(location.state);

  if (sessionQuery.data?.authenticated) {
    return <Navigate to={returnTo} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      await loginMutation.mutateAsync({ email, password });
      navigate(returnTo, { replace: true });
    } catch {
      // Mutation state renders the stable API error below.
    }
  }

  const loginError =
    loginMutation.error instanceof ApiError
      ? loginMutation.error.message
      : loginMutation.error instanceof Error
        ? loginMutation.error.message
        : null;

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-12 text-slate-950 sm:px-6">
      <section className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl shadow-black/30 sm:p-8">
        <div className="mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-600 text-sm font-bold text-white">
            PI
          </div>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">
            Portfolio Intelligence
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Sign in
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Use the email and password for your Portfolio Intelligence account.
          </p>
        </div>

        {sessionQuery.error instanceof Error ? (
          <div
            role="alert"
            className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
          >
            Secure session setup failed. {sessionQuery.error.message}
            <button
              type="button"
              onClick={() => void sessionQuery.refetch()}
              className="ml-2 font-semibold underline underline-offset-2"
            >
              Retry
            </button>
          </div>
        ) : null}

        {loginError ? (
          <div
            role="alert"
            className="mb-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
          >
            {loginError}
          </div>
        ) : null}

        <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)}>
          <label className="block">
            <span className="text-sm font-semibold text-slate-800">Email</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-base outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-slate-800">Password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-base outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <button
            type="submit"
            disabled={
              sessionQuery.isPending ||
              sessionQuery.isError ||
              loginMutation.isPending
            }
            className="inline-flex w-full items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white outline-none transition hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loginMutation.isPending ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
