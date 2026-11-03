import { useState } from "react";
import { useApplicationDetail, useApplicationHistory, useDeleteApplication } from "../api/applications";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import type { ApplicationDetail } from "../api/types";
import { formatDateTime, formatFeatureName, formatPercent } from "../lib/format";
import { ErrorNotice } from "./FormParts";
import { Modal } from "./Modal";
import { PredictionBadge } from "./PredictionBadge";
import { QueryBoundary } from "./QueryBoundary";

interface ApplicationDetailModalProps {
  applicationId: number;
  onClose: () => void;
}

/** Why the model scored this application as it did, and how its status has changed. */
export function ApplicationDetailModal({ applicationId, onClose }: ApplicationDetailModalProps) {
  const detail = useApplicationDetail(applicationId);
  const history = useApplicationHistory(applicationId);

  return (
    <Modal title="Application details" onClose={onClose}>
      <QueryBoundary query={detail}>
        {(application) => (
          <div className="space-y-5 text-sm">
            <div>
              <p className="font-medium text-gray-900">{application.candidate_name}</p>
              <p className="text-gray-600">{application.job_title}</p>
            </div>

            <section>
              <h3 className="mb-2 font-medium text-gray-900">Prediction</h3>
              <div className="flex items-center gap-2">
                <PredictionBadge prediction={application.prediction} message={application.prediction_message} />
                {application.prediction && (
                  <span className="text-gray-600">{formatPercent(application.prediction.probability)} probability</span>
                )}
              </div>
              {application.prediction_message && <p className="mt-2 text-gray-600">{application.prediction_message}</p>}
              {application.top_features.length > 0 && (
                <ul className="mt-3 space-y-1">
                  {application.top_features.map((item) => (
                    <li key={item.feature} className="flex justify-between gap-4">
                      <span className="text-gray-700">{formatFeatureName(item.feature)}</span>
                      <span className="tabular-nums text-gray-500">
                        value {Number(item.value.toFixed(2))}, effect {item.contribution > 0 ? "+" : ""}
                        {item.contribution.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-xs text-gray-500">A suggestion only. It never changes the status.</p>
            </section>

            <section>
              <h3 className="mb-2 font-medium text-gray-900">Status timeline</h3>
              <QueryBoundary
                query={history}
                isEmpty={(entries) => entries.length === 0}
                emptyMessage={`Still ${application.status}. No status changes yet.`}
              >
                {(entries) => (
                  <ol className="space-y-2">
                    {entries.map((entry) => (
                      <li key={entry.id}>
                        <p className="text-gray-800">
                          {entry.old_status} &rarr; {entry.new_status}
                        </p>
                        <p className="text-xs text-gray-500">
                          {entry.changed_by_name}, {formatDateTime(entry.changed_at)}
                        </p>
                      </li>
                    ))}
                  </ol>
                )}
              </QueryBoundary>
            </section>

            <DeleteApplicationSection application={application} onDeleted={onClose} />
          </div>
        )}
      </QueryBoundary>
    </Modal>
  );
}

function DeleteApplicationSection({ application, onDeleted }: { application: ApplicationDetail; onDeleted: () => void }) {
  const deleteApplication = useDeleteApplication();
  const [message, setMessage] = useState<string | null>(null);

  function handleDelete() {
    if (!window.confirm("Delete this application? The record stays in the database.")) return;
    setMessage(null);
    deleteApplication.mutate(
      { id: application.id, version: application.version },
      {
        onSuccess: onDeleted,
        onError: (error) => setMessage(error instanceof ApiError && error.isStale ? STALE_UPDATE_MESSAGE : error.message),
      },
    );
  }

  return (
    <section className="space-y-2 border-t border-gray-100 pt-4">
      <ErrorNotice message={message} />
      <button type="button" className="btn-danger" disabled={deleteApplication.isPending} onClick={handleDelete}>
        Delete application
      </button>
    </section>
  );
}
