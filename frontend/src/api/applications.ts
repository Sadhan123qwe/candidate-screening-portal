import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, apiDownload, apiRequest, STALE_UPDATE_MESSAGE } from "./client";
import type {
  Application,
  ApplicationDetail,
  ApplicationPage,
  ApplicationStatus,
  ApplicationSummary,
  StatusHistoryEntry,
} from "./types";

export interface ApplicationFilters {
  job_id?: number;
  status?: string;
  prediction?: string;
  search?: string;
  sort?: string;
  page: number;
  page_size: number;
}

export const APPLICATION_SORTS = [
  { value: "date_desc", label: "Newest first" },
  { value: "date_asc", label: "Oldest first" },
  { value: "probability_desc", label: "Highest match" },
  { value: "probability_asc", label: "Lowest match" },
];

export type ApplicationSummaryFilters = Pick<ApplicationFilters, "job_id" | "prediction" | "search">;

export function useApplications(filters: ApplicationFilters) {
  return useQuery({
    queryKey: ["applications", filters],
    queryFn: () => apiRequest<ApplicationPage>("/api/applications", { query: { ...filters } }),
    // Keep the current page on screen while the next one loads, so the table doesn't flicker.
    placeholderData: keepPreviousData,
  });
}

export function useApplicationSummary(filters: ApplicationSummaryFilters) {
  return useQuery({
    queryKey: ["applications", "summary", filters],
    queryFn: () => apiRequest<ApplicationSummary>("/api/applications/summary", { query: { ...filters } }),
    placeholderData: keepPreviousData,
  });
}

/** Downloads every row matching the filters, not just the page on screen. */
export function useExportApplications() {
  return useMutation({
    // Not a data change, so it's excluded from the refresh that follows other writes.
    meta: { skipRefresh: true },
    mutationFn: (filters: Omit<ApplicationFilters, "page" | "page_size">) =>
      apiDownload("/api/applications/export", "applications.csv", { ...filters }),
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

/**
 * Sends the version on screen with every change. The UI always shows what the server last
 * said, so a failed update can't leave a status on screen that was never saved.
 */
export function useStatusChange(application: Pick<Application, "id" | "version">) {
  const updateStatus = useUpdateStatus();
  const [message, setMessage] = useState<string | null>(null);

  function changeStatus(status: ApplicationStatus) {
    setMessage(null);
    updateStatus.mutate(
      { id: application.id, status, version: application.version },
      {
        onError: (error) => {
          // On a stale update, the query client has already started reloading the row.
          const isStale = error instanceof ApiError && error.isStale;
          setMessage(isStale ? STALE_UPDATE_MESSAGE : error.message);
        },
      },
    );
  }

  return { changeStatus, isPending: updateStatus.isPending, message };
}

export function useDeleteApplication() {
  return useMutation({
    mutationFn: ({ id, version }: { id: number; version: number }) =>
      apiRequest<void>(`/api/applications/${id}`, { method: "DELETE", query: { version } }),
  });
}
