import { MutationCache, QueryClient } from "@tanstack/react-query";
import { ApiError } from "./client";

/**
 * One write can affect many screens: a status change alters the table, the job's counts
 * and the candidate's page. So every write refreshes all data, rather than each mutation
 * having to know what depends on it.
 */
export function createQueryClient(options: { retry?: boolean } = {}): QueryClient {
  const client: QueryClient = new QueryClient({
    mutationCache: new MutationCache({
      onSuccess: (_data, _variables, _context, mutation) => {
        if (!mutation.meta?.skipRefresh) void client.invalidateQueries();
      },
      onError: (error) => {
        // Someone else changed the record, so the copy on screen is out of date.
        if (error instanceof ApiError && error.isStale) {
          void client.invalidateQueries();
        }
      },
    }),
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          if (options.retry === false) return false;
          // A 404 or 422 will fail the same way again. Network and server errors may not.
          const isClientError = error instanceof ApiError && error.status >= 400 && error.status < 500;
          return !isClientError && failureCount < 2;
        },
      },
    },
  });
  return client;
}
