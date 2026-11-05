import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useCreateJob, useJobs, useJobSummaries } from "../api/jobs";
import { JobForm } from "../components/JobForm";
import { QueryBoundary } from "../components/QueryBoundary";
import { Button } from "../components/ui/Button";
import { GlassCard } from "../components/ui/GlassCard";
import { PageHeader } from "../components/ui/PageHeader";
import { SkillTag } from "../components/ui/SkillTag";
import { formatYears } from "../lib/format";

const NOT_AVAILABLE = "\u2013";

export function JobsPage() {
  const jobs = useJobs();
  const summaries = useJobSummaries();
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
                  <table className="data-table jobs-table min-w-[590px]">
                    <thead>
                      <tr>
                        <th scope="col">Job</th>
                        <th scope="col">Required skills</th>
                        <th scope="col">Applied</th>
                        <th scope="col">Shortlisted</th>
                        <th scope="col">Rejected</th>
                        <th scope="col">Potential match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((job) => {
                        const summary = summaries.data?.find((item) => item.job_id === job.id);
                        return (
                        <tr key={job.id}>
                          <td>
                            <Link className="cell-link cell-title" to={`/jobs/${job.id}`}>
                              {job.title}
                            </Link>
                            <span className="cell-sub whitespace-nowrap">
                              Min. <span className="num">{formatYears(job.min_experience_years)}</span>
                            </span>
                          </td>
                          <td>
                            <div className="skill-list">
                              {job.required_skills.map((skill) => (
                                <SkillTag key={skill} skill={skill} />
                              ))}
                            </div>
                          </td>
                          <td className="num">{summary?.applied ?? NOT_AVAILABLE}</td>
                          <td className="num">{summary?.shortlisted ?? NOT_AVAILABLE}</td>
                          <td className="num">{summary?.rejected ?? NOT_AVAILABLE}</td>
                          <td className="num">{summary?.potential_match ?? NOT_AVAILABLE}</td>
                        </tr>
                        );
                      })}
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
