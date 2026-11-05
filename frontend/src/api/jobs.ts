import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { Job, JobInput, JobSummary } from "./types";

export function useJobs() {
  return useQuery({ queryKey: ["jobs"], queryFn: () => apiRequest<Job[]>("/api/jobs") });
}

export function useJobSummaries() {
  return useQuery({ queryKey: ["jobs", "summary"], queryFn: () => apiRequest<JobSummary[]>("/api/jobs/summary") });
}

export function useJob(id: number) {
  return useQuery({ queryKey: ["jobs", id], queryFn: () => apiRequest<Job>(`/api/jobs/${id}`) });
}

export function useCreateJob() {
  return useMutation({
    mutationFn: (body: JobInput) => apiRequest<Job>("/api/jobs", { method: "POST", body }),
  });
}

export function useUpdateJob() {
  return useMutation({
    mutationFn: ({ id, version, input }: { id: number; version: number; input: JobInput }) =>
      apiRequest<Job>(`/api/jobs/${id}`, { method: "PATCH", body: { version, ...input } }),
  });
}

export function useDeleteJob() {
  return useMutation({
    mutationFn: ({ id, version }: { id: number; version: number }) =>
      apiRequest<void>(`/api/jobs/${id}`, { method: "DELETE", query: { version } }),
  });
}
