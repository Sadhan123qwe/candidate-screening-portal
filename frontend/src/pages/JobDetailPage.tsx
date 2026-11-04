import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useApplications } from "../api/applications";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import { useDeleteJob, useJob, useUpdateJob } from "../api/jobs";
import type { Job, JobInput } from "../api/types";
import { APPLICATION_STATUSES } from "../api/types";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { JobForm } from "../components/JobForm";
import { Pagination } from "../components/Pagination";
import { QueryBoundary } from "../components/QueryBoundary";
import { Button } from "../components/ui/Button";
import { GlassCard } from "../components/ui/GlassCard";
import { ErrorNotice, WarningNotice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { SkillTag } from "../components/ui/SkillTag";
import { formatYears } from "../lib/format";

const PAGE_SIZE = 25;

export function JobDetailPage() {
  const jobId = Number(useParams().id);
  const job = useJob(jobId);

  return (
    <div>
      <QueryBoundary query={job}>
        {(data) => (
          <>
            <nav aria-label="Breadcrumb" className="mb-[14px] flex flex-wrap gap-x-3 leading-5">
              <Link to="/jobs" className="cell-link text-muted">
                Jobs
              </Link>
              <span aria-hidden="true" className="text-muted">
                /
              </span>
              <span aria-current="page">{data.title}</span>
            </nav>
            <JobSummary job={data} />
          </>
        )}
      </QueryBoundary>
      <div className="mt-5">
        <JobApplications jobId={jobId} />
      </div>
    </div>
  );
}

function SkillGroup({ title, skills }: { title: string; skills: string[] }) {
  return (
    <div>
      <dt className="eyebrow">{title}</dt>
      <dd className="skill-list mt-[10px]">
        {skills.length === 0 && <span className="text-muted">None</span>}
        {skills.map((skill) => (
          <SkillTag key={skill} skill={skill} />
        ))}
      </dd>
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
    <>
      <PageHeader
        title={job.title}
        subtitle={
          <>
            Minimum experience: <span className="num">{formatYears(job.min_experience_years)}</span>
          </>
        }
        aside={
          !isEditing && (
            <div className="flex gap-2">
              <Button onClick={() => setIsEditing(true)}>Edit</Button>
              <Button className="btn-danger-text" disabled={deleteJob.isPending} onClick={handleDelete}>
                Delete
              </Button>
            </div>
          )
        }
      />

      <GlassCard as="section" className="space-y-4">
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
            {job.description && <p className="text-muted">{job.description}</p>}
            <dl className="grid gap-4 sm:grid-cols-2">
              <SkillGroup title="Required skills" skills={job.required_skills} />
              <SkillGroup title="Preferred skills" skills={job.preferred_skills} />
            </dl>
            <dl className="grid grid-cols-3 gap-3 border-t border-line pt-4">
              {APPLICATION_STATUSES.map((status) => (
                <div key={status}>
                  <dt className="eyebrow">{status}</dt>
                  <dd className="num mt-1 text-[24px] leading-[30px]">{job.application_counts[status]}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </GlassCard>
    </>
  );
}

function JobApplications({ jobId }: { jobId: number }) {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page")) || 1;
  const applications = useApplications({ job_id: jobId, page, page_size: PAGE_SIZE });

  return (
    <section className="page-stack" aria-label="Applications">
      <h2 className="card-title">Applications</h2>
      <QueryBoundary query={applications} isEmpty={(data) => data.items.length === 0} emptyMessage="No applications for this job yet.">
        {(data) => (
          <>
            <GlassCard padding="none" className="overflow-hidden">
              <ApplicationsTable applications={data.items} hideJob />
            </GlassCard>
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onPageChange={(next) => setParams({ page: String(next) })}
            />
          </>
        )}
      </QueryBoundary>
    </section>
  );
}
