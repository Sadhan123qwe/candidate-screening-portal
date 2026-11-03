import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useCandidate, useDeleteCandidate, useUpdateCandidate } from "../api/candidates";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import type { CandidateDetail, CandidateInput } from "../api/types";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { CandidateForm } from "../components/CandidateForm";
import { ErrorNotice, WarningNotice } from "../components/FormParts";
import { QueryBoundary } from "../components/QueryBoundary";
import { SkillList } from "../components/SkillList";
import { formatYears } from "../lib/format";

export function CandidateDetailPage() {
  const candidate = useCandidate(Number(useParams().id));

  return (
    <div className="space-y-4">
      <Link to="/candidates" className="link text-sm">
        &larr; All candidates
      </Link>
      <QueryBoundary query={candidate}>
        {(data) => (
          <>
            <CandidateSummary candidate={data} />
            <div className="card overflow-hidden">
              <h2 className="border-b border-gray-200 px-4 py-3 text-sm font-semibold text-gray-900">Applications</h2>
              {data.applications.length === 0 ? (
                <p className="py-12 text-center text-sm text-gray-500">This candidate hasn't applied to any jobs yet.</p>
              ) : (
                <ApplicationsTable applications={data.applications} hideCandidate />
              )}
            </div>
          </>
        )}
      </QueryBoundary>
    </div>
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
    <div className="card space-y-4 p-5">
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
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">{candidate.name}</h1>
              <p className="text-sm text-gray-600">
                {candidate.email} &middot; {formatYears(candidate.experience_years)} of experience
              </p>
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn-secondary" onClick={() => setIsEditing(true)}>
                Edit
              </button>
              <button type="button" className="btn-danger" disabled={deleteCandidate.isPending} onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>
          {candidate.profile_summary && <p className="text-sm text-gray-700">{candidate.profile_summary}</p>}
          <div>
            <h2 className="mb-1 text-sm font-medium text-gray-700">Skills</h2>
            <SkillList skills={candidate.skills} />
          </div>
        </>
      )}
    </div>
  );
}
