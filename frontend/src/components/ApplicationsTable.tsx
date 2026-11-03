import { useState } from "react";
import { Link } from "react-router-dom";
import type { Application } from "../api/types";
import { formatDate } from "../lib/format";
import { ApplicationDetailModal } from "./ApplicationDetailModal";
import { PredictionBadge } from "./PredictionBadge";
import { StatusSelect } from "./StatusSelect";

interface ApplicationsTableProps {
  applications: Application[];
  /** Hide a column when the page is already about that candidate or job. */
  hideCandidate?: boolean;
  hideJob?: boolean;
}

export function ApplicationsTable({ applications, hideCandidate, hideJob }: ApplicationsTableProps) {
  const [detailId, setDetailId] = useState<number | null>(null);

  return (
    <>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
            <tr>
              {!hideCandidate && <th className="px-4 py-2">Candidate</th>}
              {!hideJob && <th className="px-4 py-2">Job</th>}
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Prediction</th>
              <th className="px-4 py-2">Created</th>
              <th className="px-4 py-2">
                <span className="sr-only">Details</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {applications.map((application) => (
              <tr key={application.id}>
                {!hideCandidate && (
                  <td className="px-4 py-2">
                    <Link className="link" to={`/candidates/${application.candidate_id}`}>
                      {application.candidate_name}
                    </Link>
                  </td>
                )}
                {!hideJob && (
                  <td className="px-4 py-2">
                    <Link className="link" to={`/jobs/${application.job_id}`}>
                      {application.job_title}
                    </Link>
                  </td>
                )}
                <td className="px-4 py-2">
                  <StatusSelect application={application} />
                </td>
                <td className="px-4 py-2">
                  <PredictionBadge prediction={application.prediction} message={application.prediction_message} />
                </td>
                <td className="whitespace-nowrap px-4 py-2 text-gray-600">{formatDate(application.created_at)}</td>
                <td className="px-4 py-2 text-right">
                  <button type="button" className="link text-sm" onClick={() => setDetailId(application.id)}>
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {detailId !== null && <ApplicationDetailModal applicationId={detailId} onClose={() => setDetailId(null)} />}
    </>
  );
}
