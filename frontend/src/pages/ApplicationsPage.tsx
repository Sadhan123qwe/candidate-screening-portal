import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApplications } from "../api/applications";
import { useJobs } from "../api/jobs";
import { APPLICATION_STATUSES } from "../api/types";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { AssignModal } from "../components/AssignModal";
import { Pagination } from "../components/Pagination";
import { QueryBoundary } from "../components/QueryBoundary";
import { SearchBox } from "../components/SearchBox";

const PAGE_SIZE = 25;

export function ApplicationsPage() {
  // Filters live in the URL, so a filtered view can be refreshed, bookmarked or shared.
  const [params, setParams] = useSearchParams();
  const [isAssigning, setIsAssigning] = useState(false);

  const jobId = params.get("job_id") ?? "";
  const status = params.get("status") ?? "";
  const search = params.get("search") ?? "";
  const page = Number(params.get("page")) || 1;

  const jobs = useJobs();
  const applications = useApplications({
    job_id: jobId ? Number(jobId) : undefined,
    status: status || undefined,
    search: search || undefined,
    page,
    page_size: PAGE_SIZE,
  });

  const updateParams = useCallback(
    (changes: Record<string, string>) => {
      setParams((current) => {
        const next = new URLSearchParams(current);
        // A new filter changes which rows exist, so the old page number no longer applies.
        if (!("page" in changes)) next.delete("page");
        for (const [key, value] of Object.entries(changes)) {
          if (value) next.set(key, value);
          else next.delete(key);
        }
        return next;
      });
    },
    [setParams],
  );

  const handleSearch = useCallback((value: string) => updateParams({ search: value }), [updateParams]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold text-gray-900">Applications</h1>
        <button type="button" className="btn-primary" onClick={() => setIsAssigning(true)}>
          Assign candidate to job
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <select aria-label="Filter by job" className="input" value={jobId} onChange={(event) => updateParams({ job_id: event.target.value })}>
          <option value="">All jobs</option>
          {jobs.data?.map((job) => (
            <option key={job.id} value={job.id}>
              {job.title}
            </option>
          ))}
        </select>
        <select aria-label="Filter by status" className="input" value={status} onChange={(event) => updateParams({ status: event.target.value })}>
          <option value="">All statuses</option>
          {APPLICATION_STATUSES.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <SearchBox label="Search applications" placeholder="Search candidate, email or job" value={search} onChange={handleSearch} />
      </div>

      <div className="card overflow-hidden">
        <QueryBoundary
          query={applications}
          isEmpty={(data) => data.items.length === 0}
          emptyMessage="No applications match these filters."
        >
          {(data) => (
            <>
              <ApplicationsTable applications={data.items} />
              <Pagination
                page={data.page}
                pageSize={data.page_size}
                total={data.total}
                onPageChange={(next) => updateParams({ page: String(next) })}
              />
            </>
          )}
        </QueryBoundary>
      </div>

      {isAssigning && <AssignModal onClose={() => setIsAssigning(false)} />}
    </div>
  );
}
