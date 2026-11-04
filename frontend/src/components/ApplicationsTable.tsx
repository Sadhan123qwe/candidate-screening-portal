import { Link, useLocation } from "react-router-dom";
import type { Application } from "../api/types";
import { formatYears } from "../lib/format";
import { PredictionBadge } from "./ui/PredictionBadge";
import { StatusPill } from "./ui/StatusPill";

interface ApplicationsTableProps {
  applications: Application[];
  /** Hide a column when the page is already about that candidate or job. */
  hideCandidate?: boolean;
  hideJob?: boolean;
}

export function ApplicationsTable({ applications, hideCandidate, hideJob }: ApplicationsTableProps) {
  const location = useLocation();

  return (
    <div className="table-scroll">
      <table className="data-table min-w-[900px]">
        <thead>
          <tr>
            {!hideCandidate && <th scope="col">Candidate</th>}
            {!hideJob && <th scope="col">Job</th>}
            <th scope="col">Required skills</th>
            <th scope="col">Experience</th>
            <th scope="col">Prediction</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {applications.map((application) => (
            <tr key={application.id}>
              {!hideCandidate && (
                <td>
                  <Link className="cell-link cell-title" to={`/candidates/${application.candidate_id}`}>
                    {application.candidate_name}
                  </Link>
                  <span className="cell-sub">{application.candidate_email}</span>
                </td>
              )}
              {!hideJob && (
                <td>
                  <Link className="cell-link" to={`/jobs/${application.job_id}`}>
                    {application.job_title}
                  </Link>
                </td>
              )}
              <td className="num whitespace-nowrap">
                {application.required_matched} / {application.required_total}
              </td>
              <td className="num whitespace-nowrap">{formatYears(application.candidate_experience_years)}</td>
              <td>
                <PredictionBadge prediction={application.prediction} message={application.prediction_message} />
              </td>
              <td>
                <StatusPill application={application} />
              </td>
              <td className="whitespace-nowrap text-right">
                <Link
                  className="link font-normal"
                  to={`/applications/${application.id}`}
                  // Lets the breadcrumb on the detail page return to this same filtered view.
                  state={{ fromSearch: location.search }}
                  aria-label={`Open application: ${application.candidate_name}, ${application.job_title}`}
                >
                  Open &rarr;
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
