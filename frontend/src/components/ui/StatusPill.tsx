import { useStatusChange } from "../../api/applications";
import { APPLICATION_STATUSES, type Application, type ApplicationStatus } from "../../api/types";

const STATUS_CLASS: Record<ApplicationStatus, string> = {
  Applied: "status-applied",
  Shortlisted: "status-shortlisted",
  Rejected: "status-rejected",
};

type StatusPillProps = {
  application: Pick<Application, "id" | "version" | "status" | "candidate_name">;
};

/**
 * A pill that opens the status control. The real select sits invisibly on top, so the
 * browser's keyboard, screen reader and touch behaviour all still apply.
 */
export function StatusPill({ application }: StatusPillProps) {
  const { changeStatus, isPending, message } = useStatusChange(application);

  return (
    <div>
      <span className={`pill status-pill ${STATUS_CLASS[application.status]}`}>
        {application.status}
        <svg aria-hidden="true" width="8" height="6" viewBox="0 0 8 6" fill="currentColor">
          <path d="M0 0h8L4 6z" />
        </svg>
        <select
          aria-label={`Status for ${application.candidate_name}`}
          value={application.status}
          disabled={isPending}
          onChange={(event) => changeStatus(event.target.value as ApplicationStatus)}
        >
          {APPLICATION_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </span>
      {message && (
        <p role="alert" className="mt-1 max-w-[14rem] text-[13px] text-warn">
          {message}
        </p>
      )}
    </div>
  );
}
