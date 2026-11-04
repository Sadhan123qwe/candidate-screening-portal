import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApplications, useApplicationSummary } from "../api/applications";
import { useJobs } from "../api/jobs";
import { useStats } from "../api/stats";
import { APPLICATION_STATUSES, PREDICTION_LABELS } from "../api/types";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { AssignModal } from "../components/AssignModal";
import { Pagination } from "../components/Pagination";
import { QueryBoundary } from "../components/QueryBoundary";
import { SearchBox } from "../components/SearchBox";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Controls";
import { FilterChip } from "../components/ui/FilterChip";
import { GlassCard } from "../components/ui/GlassCard";
import { PageHeader } from "../components/ui/PageHeader";

const PAGE_SIZE = 25;

export function ApplicationsPage() {
  // Filters live in the URL, so a filtered view can be refreshed, bookmarked or shared.
  const [params, setParams] = useSearchParams();
  const [isAssigning, setIsAssigning] = useState(false);

  const jobId = params.get("job_id") ?? "";
  const status = params.get("status") ?? "";
  const prediction = params.get("prediction") ?? "";
  const search = params.get("search") ?? "";
  const page = Number(params.get("page")) || 1;

  const sharedFilters = {
    job_id: jobId ? Number(jobId) : undefined,
    prediction: prediction || undefined,
    search: search || undefined,
  };

  const jobs = useJobs();
  const stats = useStats();
  const applications = useApplications({ ...sharedFilters, status: status || undefined, page, page_size: PAGE_SIZE });
  const summary = useApplicationSummary(sharedFilters);

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

  const statusChips = [
    { label: "All", value: "", count: summary.data?.total },
    { label: "Applied", value: "Applied", count: summary.data?.applied },
    { label: "Shortlisted", value: "Shortlisted", count: summary.data?.shortlisted },
    { label: "Rejected", value: "Rejected", count: summary.data?.rejected },
  ];

  return (
    <div>
      <PageHeader
        title="Applications"
        subtitle={
          stats.data
            ? `${stats.data.applications} applications across ${stats.data.jobs} jobs. The prediction is a hint; you set the status.`
            : "The prediction is a hint; you set the status."
        }
        aside={
          <Button variant="primary" onClick={() => setIsAssigning(true)}>
            + Assign candidate
          </Button>
        }
      />

      <div className="page-stack">
        <div role="group" aria-label="Filter by status count" className="flex flex-wrap gap-2">
          {statusChips.map((chip) => (
            <FilterChip
              key={chip.label}
              label={chip.label}
              count={chip.count}
              active={status === chip.value}
              onClick={() => updateParams({ status: chip.value })}
            />
          ))}
        </div>

        <GlassCard padding="sm" className="filter-bar">
          <SearchBox
            id="filter-search"
            label="Search applications"
            visibleLabel="Search"
            placeholder="Candidate name, email or job"
            value={search}
            onChange={handleSearch}
          />
          <Select
            id="filter-job"
            label="Job"
            aria-label="Filter by job"
            value={jobId}
            onChange={(event) => updateParams({ job_id: event.target.value })}
          >
            <option value="">All jobs</option>
            {jobs.data?.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </Select>
          <Select
            id="filter-status"
            label="Status"
            aria-label="Filter by status"
            value={status}
            onChange={(event) => updateParams({ status: event.target.value })}
          >
            <option value="">All statuses</option>
            {APPLICATION_STATUSES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
          <Select
            id="filter-prediction"
            label="Prediction"
            aria-label="Filter by prediction"
            value={prediction}
            onChange={(event) => updateParams({ prediction: event.target.value })}
          >
            <option value="">Any prediction</option>
            {PREDICTION_LABELS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        </GlassCard>

        <QueryBoundary
          query={applications}
          isEmpty={(data) => data.items.length === 0}
          emptyMessage="No applications match these filters."
          emptyAction={
            params.toString() ? (
              <Button onClick={() => setParams({})}>Clear filters</Button>
            ) : (
              <Button onClick={() => setIsAssigning(true)}>Assign a candidate</Button>
            )
          }
        >
          {(data) => (
            <>
              <GlassCard padding="none" className="overflow-hidden">
                <ApplicationsTable applications={data.items} />
              </GlassCard>
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
