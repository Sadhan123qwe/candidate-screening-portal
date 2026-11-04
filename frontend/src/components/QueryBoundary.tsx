import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { EmptyState, ErrorState, LoadingState } from "./ui/States";

interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>;
  isEmpty?: (data: T) => boolean;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  children: (data: T) => ReactNode;
}

/** Gives every query the same loading, error-with-retry and empty states. */
export function QueryBoundary<T>({ query, isEmpty, emptyMessage, emptyAction, children }: QueryBoundaryProps<T>) {
  if (query.isPending) return <LoadingState />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />;
  if (isEmpty?.(query.data)) return <EmptyState message={emptyMessage ?? "Nothing to show yet."} action={emptyAction} />;
  return <>{children(query.data)}</>;
}
