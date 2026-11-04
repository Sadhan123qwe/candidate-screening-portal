import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useCreateJob, useJobs } from "../api/jobs";
import type { Job } from "../api/types";
import { JobForm } from "../components/JobForm";
import { QueryBoundary } from "../components/QueryBoundary";
import { Button } from "../components/ui/Button";
import { GlassCard } from "../components/ui/GlassCard";
import { PageHeader } from "../components/ui/PageHeader";
import { SkillTag } from "../components/ui/SkillTag";
import { formatYears } from "../lib/format";

function totalApplications(job: Job): number {
  const { Applied, Shortlisted, Rejected } = job.application_counts;
  return Applied + Shortlisted + Rejected;
}

export function JobsPage() {
  const jobs = useJobs();
  const createJob = useCreateJob();
  const titleRef = useRef<HTMLInputElement>(null);
  // A new key remounts the form, which is the simplest way to clear every field.
  const [formKey, setFormKey] = useState(0);

  function resetForm() {
    setFormKey((key) => key + 1);
    createJob.reset();
  }

  const count = jobs.data?.length;
  const subtitle = "Required skills drive the prediction most.";

  return (
    <div>
      <PageHeader
        title="Jobs"
        subtitle={count === undefined ? subtitle : `${count} open ${count === 1 ? "internship" : "internships"}. ${subtitle}`}
        aside={
          <Button variant="primary" onClick={() => titleRef.current?.focus()}>
            + New job
          </Button>
        }
      />

      <div className="split-grid">
        <div>
          <QueryBoundary
            query={jobs}
            isEmpty={(list) => list.length === 0}
            emptyMessage="No jobs yet. Create the first one."
            emptyAction={<Button onClick={() => titleRef.current?.focus()}>New job</Button>}
          >
            {(list) => (
              <GlassCard padding="none" className="overflow-hidden">
                <div className="table-scroll">
                  <table className="data-table min-w-[560px]">
                    <thead>
                      <tr>
                        <th scope="col">Job</th>
                        <th scope="col">Required skills</th>
                        <th scope="col" className="w-[76px]">
                          Min exp.
                        </th>
                        <th scope="col">Applications</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((job) => (
                        <tr key={job.id}>
                          <td>
                            <Link className="cell-link cell-title" to={`/jobs/${job.id}`}>
                              {job.title}
                            </Link>
                          </td>
                          <td>
                            <div className="skill-list">
                              {job.required_skills.map((skill) => (
                                <SkillTag key={skill} skill={skill} />
                              ))}
                            </div>
                          </td>
                          <td className="num whitespace-nowrap">{formatYears(job.min_experience_years)}</td>
                          <td className="num">{totalApplications(job)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            )}
          </QueryBoundary>
        </div>

        <GlassCard as="section" aria-label="New job" className="split-form">
          <h2 className="card-title">New job</h2>
          <div className="mt-[13px]">
            <JobForm
              key={formKey}
              ref={titleRef}
              submitLabel="Create job"
              isSubmitting={createJob.isPending}
              serverError={createJob.error}
              onSubmit={(input) => createJob.mutate(input, { onSuccess: resetForm })}
              onCancel={resetForm}
            />
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
