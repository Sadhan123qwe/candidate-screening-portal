import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest, getToken, setToken } from "./client";
import type { LoginResponse, User } from "./types";

export function useLogin() {
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const response = await apiRequest<LoginResponse>("/api/auth/login", { method: "POST", body: credentials });
      setToken(response.access_token);
      return response.user;
    },
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiRequest<User>("/api/auth/me"),
    enabled: Boolean(getToken()),
  });
}
