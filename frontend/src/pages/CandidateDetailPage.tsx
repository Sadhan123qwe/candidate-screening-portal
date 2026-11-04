import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useCandidate, useDeleteCandidate, useUpdateCandidate } from "../api/candidates";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import type { CandidateDetail, CandidateInput } from "../api/types";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { CandidateForm } from "../components/CandidateForm";
import { QueryBoundary } from "../components/QueryBoundary";
import { Button } from "../components/ui/Button";
import { GlassCard } from "../components/ui/GlassCard";
import { ErrorNotice, WarningNotice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { SkillTag } from "../components/ui/SkillTag";
import { EmptyState } from "../components/ui/States";
import { formatYears } from "../lib/format";

export function CandidateDetailPage() {
  const candidate = useCandidate(Number(useParams().id));

  return (
    <QueryBoundary query={candidate}>
      {(data) => (
        <div>
          <nav aria-label="Breadcrumb" className="mb-[14px] flex flex-wrap gap-x-3 leading-5">
            <Link to="/candidates" className="cell-link text-muted">
              Candidates
            </Link>
            <span aria-hidden="true" className="text-muted">
              /
            </span>
            <span aria-current="page">{data.name}</span>
          </nav>
          <CandidateSummary candidate={data} />
          <section className="page-stack mt-5" aria-label="Applications">
            <h2 className="card-title">Applications</h2>
            {data.applications.length === 0 ? (
              <EmptyState message="This candidate hasn't applied to any jobs yet." />
            ) : (
              <GlassCard padding="none" className="overflow-hidden">
                <ApplicationsTable applications={data.applications} hideCandidate />
              </GlassCard>
            )}
          </section>
        </div>
      )}
    </QueryBoundary>
  );
}

function CandidateSummary({ candidate }: { candidate: CandidateDetail }) {
  const navigate = useNavigate();
  const updateCandidate = useUpdateCandidate();
  const deleteCandidate = useDeleteCandidate();
  const [isEditing, setIsEditing] = useState(false);
  const [staleNotice, setStaleNotice] = useState<string | null>(null);

  function handleSave(input: CandidateInput) {
    setStaleNotice(null);
    updateCandidate.mutate(
      { id: candidate.id, version: candidate.version, input },
      {
        onSuccess: () => setIsEditing(false),
        onError: (error) => {
          if (error instanceof ApiError && error.isStale) {
            // The latest data is reloading, and the form below resets to it via its key.
            setStaleNotice(STALE_UPDATE_MESSAGE);
            updateCandidate.reset();
          }
        },
      },
    );
  }

  function handleDelete() {
    if (!window.confirm(`Delete ${candidate.name} and hide their applications? The records stay in the database.`)) return;
    setStaleNotice(null);
    deleteCandidate.mutate(
      { id: candidate.id, version: candidate.version },
      {
        onSuccess: () => navigate("/candidates"),
        onError: (error) => {
          if (error instanceof ApiError && error.isStale) {
            setStaleNotice(STALE_UPDATE_MESSAGE);
            deleteCandidate.reset();
          }
        },
      },
    );
  }

  return (
    <>
      <PageHeader
        title={candidate.name}
        subtitle={
          <>
            {candidate.email} &middot; <span className="num">{formatYears(candidate.experience_years)}</span> of experience
          </>
        }
        aside={
          !isEditing && (
            <div className="flex gap-2">
              <Button onClick={() => setIsEditing(true)}>Edit</Button>
              <Button className="btn-danger-text" disabled={deleteCandidate.isPending} onClick={handleDelete}>
                Delete
              </Button>
            </div>
          )
        }
      />

      <GlassCard as="section" className="space-y-4">
        <WarningNotice message={staleNotice} />
        <ErrorNotice message={deleteCandidate.error?.message} />

        {isEditing ? (
          <CandidateForm
            // A new version remounts the form, so it can't keep showing out-of-date values.
            key={candidate.version}
            candidate={candidate}
            submitLabel="Save changes"
            isSubmitting={updateCandidate.isPending}
            serverError={updateCandidate.error}
            onSubmit={handleSave}
            onCancel={() => {
              setIsEditing(false);
              updateCandidate.reset();
            }}
          />
        ) : (
          <>
            {candidate.profile_summary && <p className="text-muted">{candidate.profile_summary}</p>}
            <div>
              <h3 className="eyebrow">Skills</h3>
              <div className="skill-list mt-[10px]">
                {candidate.skills.map((skill) => (
                  <SkillTag key={skill} skill={skill} />
                ))}
              </div>
            </div>
          </>
        )}
      </GlassCard>
    </>
  );
}
