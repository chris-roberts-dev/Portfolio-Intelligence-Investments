import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import {
  fetchAuthSession,
  loginWithPassword,
  logoutSession,
  type AuthSessionResult,
  type LoginRequest,
} from "../api/auth";

export const AUTH_SESSION_QUERY_KEY = ["auth","session"] as const;

function clearOwnerScopedQueries(queryClient: QueryClient) {
  queryClient.removeQueries({
    predicate: (query) => {
      const root = query.queryKey[0];
      return (
        root === "portfolios" ||
        (typeof root === "string" && root.startsWith("portfolio-"))
      );
    },
  });
}

export function useSession() {
  return useQuery({
    queryKey: AUTH_SESSION_QUERY_KEY,
    queryFn: ({ signal }) => fetchAuthSession(signal),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: LoginRequest) => loginWithPassword(request),
    onSuccess: (session: AuthSessionResult) => {
      clearOwnerScopedQueries(queryClient);
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, session);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => logoutSession(),
    onSuccess: (session: AuthSessionResult) => {
      clearOwnerScopedQueries(queryClient);
      queryClient.setQueryData(AUTH_SESSION_QUERY_KEY, session);
    },
  });
}
