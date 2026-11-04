import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useCreateApplication } from "../api/applications";
import { useCandidates } from "../api/candidates";
import { ApiError } from "../api/client";
import { useJobs } from "../api/jobs";
import type { Candidate, Job } from "../api/types";
import { Modal } from "./Modal";
import { QueryBoundary } from "./QueryBoundary";
import { Button } from "./ui/Button";
import { Select } from "./ui/Controls";

const DUPLICATE_APPLICATION = "DUPLICATE_APPLICATION";

/** Names can repeat, so the email is added only where it's needed to tell people apart. */
function candidateLabels(candidates: Candidate[]): Map<number, string> {
  const nameCounts = new Map<string, number>();
  for (const { name } of candidates) nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1);
  return new Map(
    candidates.map(({ id, name, email }) => [id, (nameCounts.get(name) ?? 0) > 1 ? `${name} (${email})` : name]),
  );
}

interface DuplicateBannerProps {
  candidate?: Candidate;
  job?: Job;
  onOpenExisting: () => void;
}

function DuplicateBanner({ candidate, job, onOpenExisting }: DuplicateBannerProps) {
  const search = new URLSearchParams({ job_id: String(job?.id ?? ""), search: candidate?.email ?? "" });
  return (
    <div role="alert" className="notice notice-bad">
      <strong className="font-semibold text-bad">Already applied.</strong> {candidate?.name} has an application for {job?.title}.
      Pick another job or{" "}
      <Link className="underline" to={`/applications?${search}`} onClick={onOpenExisting}>
        open the existing application
      </Link>
      .
    </div>
  );
}

/** Assign a candidate to a job. A duplicate shows the server's 409 inline, with a way forward. */
export function AssignModal({ onClose }: { onClose: () => void }) {
  const candidates = useCandidates();
  const jobs = useJobs();
  const createApplication = useCreateApplication();
  const [candidateId, setCandidateId] = useState("");
  const [jobId, setJobId] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    createApplication.mutate({ candidate_id: Number(candidateId), job_id: Number(jobId) }, { onSuccess: onClose });
  }

  const { error } = createApplication;
  const isDuplicate = error instanceof ApiError && error.code === DUPLICATE_APPLICATION;
  // A soft-deleted application can't be opened, so the server's own wording stays for that case.
  const hasOpenDuplicate = isDuplicate && !error.message.includes("deleted");

  return (
    <Modal title="Assign candidate to job" description="The model scores the pair as soon as you assign." onClose={onClose}>
      <QueryBoundary query={candidates}>
        {(candidateList) => (
          <QueryBoundary query={jobs}>
            {(jobList) => {
              const labels = candidateLabels(candidateList);
              return (
                <form onSubmit={handleSubmit} className="space-y-[18px]">
                  <Select id="assign-candidate" label="Candidate" required value={candidateId} onChange={(event) => setCandidateId(event.target.value)}>
                    <option value="">Choose a candidate</option>
                    {candidateList.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>
                        {labels.get(candidate.id)}
                      </option>
                    ))}
                  </Select>
                  <Select id="assign-job" label="Job" required value={jobId} onChange={(event) => setJobId(event.target.value)}>
                    <option value="">Choose a job</option>
                    {jobList.map((job) => (
                      <option key={job.id} value={job.id}>
                        {job.title}
                      </option>
                    ))}
                  </Select>
                  {hasOpenDuplicate && (
                    <DuplicateBanner
                      candidate={candidateList.find((candidate) => candidate.id === Number(candidateId))}
                      job={jobList.find((job) => job.id === Number(jobId))}
                      onOpenExisting={onClose}
                    />
                  )}
                  {error && !hasOpenDuplicate && (
                    <div role="alert" className="notice notice-bad">
                      {error.message}
                    </div>
                  )}
                  <div className="flex justify-end gap-[14px]">
                    <Button onClick={onClose}>Cancel</Button>
                    <Button type="submit" variant="primary" disabled={createApplication.isPending}>
                      {createApplication.isPending ? "Assigning..." : "Assign"}
                    </Button>
                  </div>
                </form>
              );
            }}
          </QueryBoundary>
        )}
      </QueryBoundary>
    </Modal>
  );
}
