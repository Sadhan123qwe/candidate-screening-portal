import { useState } from "react";
import { useUpdateStatus } from "../api/applications";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import { APPLICATION_STATUSES, type Application, type ApplicationStatus } from "../api/types";

/**
 * Updates status in place. The select always shows what the server last said, so a
 * failed update can't leave the screen showing a status that wasn't saved.
 */
export function StatusSelect({ application }: { application: Application }) {
  const updateStatus = useUpdateStatus();
  const [message, setMessage] = useState<string | null>(null);

  function handleChange(status: ApplicationStatus) {
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

  return (
    <div>
      <select
        aria-label={`Status for ${application.candidate_name}`}
        value={application.status}
        disabled={updateStatus.isPending}
        onChange={(event) => handleChange(event.target.value as ApplicationStatus)}
        className="input w-auto py-1"
      >
        {APPLICATION_STATUSES.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
      {message && (
        <p role="alert" className="mt-1 max-w-[14rem] text-xs text-amber-800">
          {message}
        </p>
      )}
    </div>
  );
}
