import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { Application, ApplicationDetail, ApplicationPage, ApplicationStatus, StatusHistoryEntry } from "./types";

export interface ApplicationFilters {
  job_id?: number;
  status?: string;
  search?: string;
  page: number;
  page_size: number;
}

export function useApplications(filters: ApplicationFilters) {
  return useQuery({
    queryKey: ["applications", filters],
    queryFn: () => apiRequest<ApplicationPage>("/api/applications", { query: { ...filters } }),
    // Keep the current page on screen while the next one loads, so the table doesn't flicker.
    placeholderData: keepPreviousData,
  });
}

export function useApplicationDetail(id: number) {
  return useQuery({
    queryKey: ["application", id],
    queryFn: () => apiRequest<ApplicationDetail>(`/api/applications/${id}`),
  });
}

export function useApplicationHistory(id: number) {
  return useQuery({
    queryKey: ["application", id, "history"],
    queryFn: () => apiRequest<StatusHistoryEntry[]>(`/api/applications/${id}/history`),
  });
}

export function useCreateApplication() {
  return useMutation({
    mutationFn: (body: { candidate_id: number; job_id: number }) =>
      apiRequest<Application>("/api/applications", { method: "POST", body }),
  });
}

export function useUpdateStatus() {
  return useMutation({
    mutationFn: ({ id, status, version }: { id: number; status: ApplicationStatus; version: number }) =>
      apiRequest<Application>(`/api/applications/${id}/status`, { method: "PATCH", body: { status, version } }),
  });
}

export function useDeleteApplication() {
  return useMutation({
    mutationFn: ({ id, version }: { id: number; version: number }) =>
      apiRequest<void>(`/api/applications/${id}`, { method: "DELETE", query: { version } }),
  });
}
