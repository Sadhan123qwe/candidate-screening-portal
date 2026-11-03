import { useState, type FormEvent } from "react";
import { useCreateApplication } from "../api/applications";
import { useCandidates } from "../api/candidates";
import { useJobs } from "../api/jobs";
import { ErrorNotice, Field } from "./FormParts";
import { Modal } from "./Modal";
import { QueryBoundary } from "./QueryBoundary";

/** Assign a candidate to a job. A duplicate shows the server's 409 message inline. */
export function AssignModal({ onClose }: { onClose: () => void }) {
  const candidates = useCandidates();
  const jobs = useJobs();
  const createApplication = useCreateApplication();
  const [candidateId, setCandidateId] = useState("");
  const [jobId, setJobId] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    createApplication.mutate(
      { candidate_id: Number(candidateId), job_id: Number(jobId) },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal title="Assign candidate to job" onClose={onClose}>
      <QueryBoundary query={candidates}>
        {(candidateList) => (
          <QueryBoundary query={jobs}>
            {(jobList) => (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Field id="assign-candidate" label="Candidate">
                  <select id="assign-candidate" className="input" required value={candidateId} onChange={(event) => setCandidateId(event.target.value)}>
                    <option value="">Choose a candidate</option>
                    {candidateList.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.name} ({candidate.email})
                      </option>
                    ))}
                  </select>
                </Field>
                <Field id="assign-job" label="Job">
                  <select id="assign-job" className="input" required value={jobId} onChange={(event) => setJobId(event.target.value)}>
                    <option value="">Choose a job</option>
                    {jobList.map((job) => (
                      <option key={job.id} value={job.id}>
                        {job.title}
                      </option>
                    ))}
                  </select>
                </Field>
                <ErrorNotice message={createApplication.error?.message} />
                <div className="flex justify-end gap-2">
                  <button type="button" className="btn-secondary" onClick={onClose}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary" disabled={createApplication.isPending}>
                    {createApplication.isPending ? "Assigning..." : "Assign"}
                  </button>
                </div>
              </form>
            )}
          </QueryBoundary>
        )}
      </QueryBoundary>
    </Modal>
  );
}
