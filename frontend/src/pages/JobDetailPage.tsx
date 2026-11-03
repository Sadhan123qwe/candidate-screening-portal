import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useApplications } from "../api/applications";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import { useDeleteJob, useJob, useUpdateJob } from "../api/jobs";
import type { Job, JobInput } from "../api/types";
import { APPLICATION_STATUSES } from "../api/types";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { ErrorNotice, WarningNotice } from "../components/FormParts";
import { JobForm } from "../components/JobForm";
import { Pagination } from "../components/Pagination";
import { QueryBoundary } from "../components/QueryBoundary";
import { SkillList } from "../components/SkillList";
import { formatYears } from "../lib/format";

const PAGE_SIZE = 25;

export function JobDetailPage() {
  const jobId = Number(useParams().id);
  const job = useJob(jobId);

  return (
    <div className="space-y-4">
      <Link to="/jobs" className="link text-sm">
        &larr; All jobs
      </Link>
      <QueryBoundary query={job}>{(data) => <JobSummary job={data} />}</QueryBoundary>
      <JobApplications jobId={jobId} />
    </div>
  );
}

function JobSummary({ job }: { job: Job }) {
  const navigate = useNavigate();
  const updateJob = useUpdateJob();
  const deleteJob = useDeleteJob();
  const [isEditing, setIsEditing] = useState(false);
  const [staleNotice, setStaleNotice] = useState<string | null>(null);

  function handleSave(input: JobInput) {
    setStaleNotice(null);
    updateJob.mutate(
      { id: job.id, version: job.version, input },
      {
        onSuccess: () => setIsEditing(false),
        onError: (error) => {
          if (error instanceof ApiError && error.isStale) {
            // The latest data is reloading, and the form below resets to it via its key.
            setStaleNotice(STALE_UPDATE_MESSAGE);
            updateJob.reset();
          }
        },
      },
    );
  }

  function handleDelete() {
    if (!window.confirm(`Delete "${job.title}" and hide its applications? The records stay in the database.`)) return;
    setStaleNotice(null);
    deleteJob.mutate(
      { id: job.id, version: job.version },
      {
        onSuccess: () => navigate("/jobs"),
        onError: (error) => {
          if (error instanceof ApiError && error.isStale) {
            setStaleNotice(STALE_UPDATE_MESSAGE);
            deleteJob.reset();
          }
        },
      },
    );
  }

  return (
    <div className="card space-y-4 p-5">
      <WarningNotice message={staleNotice} />
      <ErrorNotice message={deleteJob.error?.message} />

      {isEditing ? (
        <JobForm
          // A new version remounts the form, so it can't keep showing out-of-date values.
          key={job.version}
          job={job}
          submitLabel="Save changes"
          isSubmitting={updateJob.isPending}
          serverError={updateJob.error}
          onSubmit={handleSave}
          onCancel={() => {
            setIsEditing(false);
            updateJob.reset();
          }}
        />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{job.title}</h1>
              <p className="text-sm text-gray-600">Minimum experience: {formatYears(job.min_experience_years)}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => setIsEditing(true)}>
                Edit
              </button>
              <button type="button" className="btn-danger" disabled={deleteJob.isPending} onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>

          {job.description && <p className="text-sm text-gray-700">{job.description}</p>}

          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="mb-1 text-sm font-medium text-gray-700">Required skills</dt>
              <dd>
                <SkillList skills={job.required_skills} />
              </dd>
            </div>
            <div>
              <dt className="mb-1 text-sm font-medium text-gray-700">Preferred skills</dt>
              <dd>
                <SkillList skills={job.preferred_skills} muted />
              </dd>
            </div>
          </dl>

          <dl className="grid grid-cols-3 gap-3 border-t border-gray-100 pt-4">
            {APPLICATION_STATUSES.map((status) => (
              <div key={status}>
                <dt className="text-xs uppercase tracking-wide text-gray-500">{status}</dt>
                <dd className="text-lg font-semibold tabular-nums text-gray-900">{job.application_counts[status]}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </div>
  );
}

function JobApplications({ jobId }: { jobId: number }) {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page")) || 1;
  const applications = useApplications({ job_id: jobId, page, page_size: PAGE_SIZE });

  return (
    <div className="card overflow-hidden">
      <h2 className="border-b border-gray-200 px-4 py-3 text-sm font-semibold text-gray-900">Applications</h2>
      <QueryBoundary query={applications} isEmpty={(data) => data.items.length === 0} emptyMessage="No applications for this job yet.">
        {(data) => (
          <>
            <ApplicationsTable applications={data.items} hideJob />
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onPageChange={(next) => setParams({ page: String(next) })}
            />
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
