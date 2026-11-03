import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { ModelMetrics } from "./types";

export function useModelMetrics() {
  return useQuery({ queryKey: ["model-metrics"], queryFn: () => apiRequest<ModelMetrics>("/api/model/metrics") });
}
