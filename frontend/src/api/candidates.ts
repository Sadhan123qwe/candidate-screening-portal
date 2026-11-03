import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { Candidate, CandidateDetail, CandidateInput } from "./types";

export function useCandidates(search = "") {
  return useQuery({
    queryKey: ["candidates", search],
    queryFn: () => apiRequest<Candidate[]>("/api/candidates", { query: { search } }),
    placeholderData: keepPreviousData,
  });
}

export function useCandidate(id: number) {
  return useQuery({
    queryKey: ["candidate", id],
    queryFn: () => apiRequest<CandidateDetail>(`/api/candidates/${id}`),
  });
}

export function useCreateCandidate() {
  return useMutation({
    mutationFn: (body: CandidateInput) => apiRequest<Candidate>("/api/candidates", { method: "POST", body }),
  });
}

export function useUpdateCandidate() {
  return useMutation({
    mutationFn: ({ id, version, input }: { id: number; version: number; input: CandidateInput }) =>
      apiRequest<Candidate>(`/api/candidates/${id}`, { method: "PATCH", body: { version, ...input } }),
  });
}

export function useDeleteCandidate() {
  return useMutation({
    mutationFn: ({ id, version }: { id: number; version: number }) =>
      apiRequest<void>(`/api/candidates/${id}`, { method: "DELETE", query: { version } }),
  });
}
