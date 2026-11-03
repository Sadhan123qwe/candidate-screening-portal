import { useState } from "react";
import { Link } from "react-router-dom";
import { useCreateJob, useJobs } from "../api/jobs";
import { JobForm } from "../components/JobForm";
import { Modal } from "../components/Modal";
import { QueryBoundary } from "../components/QueryBoundary";
import { formatYears } from "../lib/format";

export function JobsPage() {
  const jobs = useJobs();
  const createJob = useCreateJob();
  const [isCreating, setIsCreating] = useState(false);

  function closeForm() {
    setIsCreating(false);
    createJob.reset();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Jobs</h1>
        <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
          New job
        </button>
      </div>

      <div className="card overflow-hidden">
        <QueryBoundary query={jobs} isEmpty={(list) => list.length === 0} emptyMessage="No jobs yet. Create the first one.">
          {(list) => (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-4 py-2">Title</th>
                    <th className="px-4 py-2">Min. experience</th>
                    <th className="px-4 py-2 text-right">Applied</th>
                    <th className="px-4 py-2 text-right">Shortlisted</th>
                    <th className="px-4 py-2 text-right">Rejected</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {list.map((job) => (
                    <tr key={job.id}>
                      <td className="px-4 py-2">
                        <Link className="link" to={`/jobs/${job.id}`}>
                          {job.title}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{formatYears(job.min_experience_years)}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-700">{job.application_counts.Applied}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-700">{job.application_counts.Shortlisted}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-gray-700">{job.application_counts.Rejected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </QueryBoundary>
      </div>

      {isCreating && (
        <Modal title="New job" onClose={closeForm}>
          <JobForm
            submitLabel="Create job"
            isSubmitting={createJob.isPending}
            serverError={createJob.error}
            onSubmit={(input) => createJob.mutate(input, { onSuccess: closeForm })}
            onCancel={closeForm}
          />
        </Modal>
      )}
    </div>
  );
}
