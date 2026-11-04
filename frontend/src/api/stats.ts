import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { PortalStats } from "./types";

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: () => apiRequest<PortalStats>("/api/stats") });
}
