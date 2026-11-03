import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>;
  isEmpty?: (data: T) => boolean;
  emptyMessage?: string;
  children: (data: T) => ReactNode;
}

/** Gives every query the same loading, error-with-retry and empty states. */
export function QueryBoundary<T>({ query, isEmpty, emptyMessage, children }: QueryBoundaryProps<T>) {
  if (query.isPending) {
    return (
      <div role="status" className="py-12 text-center text-sm text-gray-500">
        Loading...
      </div>
    );
  }

  if (query.isError) {
    return (
      <div role="alert" className="py-12 text-center">
        <p className="text-sm text-red-700">{query.error.message}</p>
        <button type="button" className="btn-secondary mt-3" onClick={() => void query.refetch()}>
          Try again
        </button>
      </div>
    );
  }

  if (isEmpty?.(query.data)) {
    return <div className="py-12 text-center text-sm text-gray-500">{emptyMessage ?? "Nothing to show yet."}</div>;
  }

  return <>{children(query.data)}</>;
}
