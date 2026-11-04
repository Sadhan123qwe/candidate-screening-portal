import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { useApplicationDetail, useApplicationHistory, useDeleteApplication, useStatusChange } from "../api/applications";
import { ApiError, STALE_UPDATE_MESSAGE } from "../api/client";
import { APPLICATION_STATUSES, type ApplicationDetail } from "../api/types";
import { QueryBoundary } from "../components/QueryBoundary";
import { Button } from "../components/ui/Button";
import { GlassCard } from "../components/ui/GlassCard";
import { ErrorNotice, WarningNotice } from "../components/ui/Notice";
import { PredictionBadge } from "../components/ui/PredictionBadge";
import { SkillTag } from "../components/ui/SkillTag";
import { StatusPill } from "../components/ui/StatusPill";
import {
  formatDate,
  formatDateTime,
  formatFeatureName,
  formatFeatureValue,
  formatPercent,
  formatPoints,
  formatSignedYears,
  formatYears,
} from "../lib/format";

export function ApplicationDetailPage() {
  const applicationId = Number(useParams().id);
  const detail = useApplicationDetail(applicationId);
  const location = useLocation();
  const fromSearch = (location.state as { fromSearch?: string } | null)?.fromSearch ?? "";
  const backTo = `/applications${fromSearch}`;

  return (
    <QueryBoundary query={detail}>
      {(application) => (
        <div>
          <nav aria-label="Breadcrumb" className="flex flex-wrap gap-x-3 leading-5">
            <Link to={backTo} className="cell-link text-muted">
              Applications
            </Link>
            <span aria-hidden="true" className="text-muted">
              /
            </span>
            <span aria-current="page">
              {application.candidate_name} &rarr; {application.job_title}
            </span>
          </nav>

          <header className="page-header mb-[15px] mt-[17px]">
            <div className="min-w-0">
              <h1 className="page-title">{application.candidate_name}</h1>
              <p className="page-subtitle">
                {application.candidate_email} &middot; applied to {application.job_title} &middot;{" "}
                {formatDate(application.created_at)}
              </p>
            </div>
            <StatusPill application={application} />
          </header>

          <div className="detail-grid">
            <div className="detail-column">
              <SkillsCard application={application} />
              <ExperienceCard application={application} />
              <HistoryCard application={application} />
            </div>
            <div className="detail-column">
              <PredictionCard application={application} />
              <SetStatusCard application={application} backTo={backTo} />
            </div>
          </div>
        </div>
      )}
    </QueryBoundary>
  );
}

function SkillGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="eyebrow">{title}</h3>
      <div className="skill-list mt-[13px]">{children}</div>
    </section>
  );
}

function SkillsCard({ application }: { application: ApplicationDetail }) {
  const { required_skills_matched: requiredHit, required_skills_missing: requiredMiss } = application;
  const { preferred_skills_matched: preferredHit, preferred_skills_missing: preferredMiss } = application;
  const requiredTotal = requiredHit.length + requiredMiss.length;
  const preferredTotal = preferredHit.length + preferredMiss.length;
  const none = <span className="text-muted">None</span>;

  return (
    <GlassCard as="section">
      <h2 className="card-title">Skills vs. job requirements</h2>
      <div className="mt-[13px] space-y-[14px]">
        <SkillGroup title={`Required · ${requiredHit.length} of ${requiredTotal}`}>
          {requiredTotal === 0 && none}
          {requiredHit.map((skill) => (
            <SkillTag key={skill} skill={skill} variant="hit" />
          ))}
          {requiredMiss.map((skill) => (
            <SkillTag key={skill} skill={skill} variant="miss" />
          ))}
        </SkillGroup>
        <SkillGroup title={`Preferred · ${preferredHit.length} of ${preferredTotal}`}>
          {preferredTotal === 0 && none}
          {preferredHit.map((skill) => (
            <SkillTag key={skill} skill={skill} variant="hit" />
          ))}
          {preferredMiss.map((skill) => (
            <SkillTag key={skill} skill={skill} variant="miss" />
          ))}
        </SkillGroup>
        <SkillGroup title="Other candidate skills">
          {application.other_candidate_skills.length === 0 && none}
          {application.other_candidate_skills.map((skill) => (
            <SkillTag key={skill} skill={skill} />
          ))}
        </SkillGroup>
      </div>
    </GlassCard>
  );
}

function ExperienceFigure({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div>
      <dt className="eyebrow">{label}</dt>
      <dd className={`num mt-1 text-[24px] leading-[30px] ${warn ? "text-warn" : ""}`}>{value}</dd>
    </div>
  );
}

function ExperienceCard({ application }: { application: ApplicationDetail }) {
  return (
    <GlassCard as="section">
      <h2 className="card-title">Experience</h2>
      <dl className="mt-[13px] flex flex-wrap gap-x-10 gap-y-3">
        <ExperienceFigure label="Candidate" value={formatYears(application.candidate_experience_years)} />
        <ExperienceFigure label="Job minimum" value={formatYears(application.job_min_experience_years)} />
        <ExperienceFigure label="Gap" value={formatSignedYears(application.experience_gap)} warn={application.experience_gap < 0} />
      </dl>
      {application.candidate_profile_summary && <p className="mt-3 text-muted">{application.candidate_profile_summary}</p>}
    </GlassCard>
  );
}

function HistoryCard({ application }: { application: ApplicationDetail }) {
  const history = useApplicationHistory(application.id);
  const created = formatDateTime(application.created_at);

  return (
    <GlassCard as="section">
      <h2 className="card-title">Status history</h2>
      <div className="mt-3">
        <QueryBoundary query={history}>
          {(entries) => (
            <ol className="timeline">
              <li>
                <p>
                  Created as <span className="font-medium">Applied</span>
                </p>
                <p className="text-muted">
                  {created}
                  {application.imported_from_dataset && " · imported from dataset"}
                </p>
              </li>
              {entries.map((entry) => (
                <li key={entry.id}>
                  <p>
                    {entry.old_status} &rarr; <span className="font-medium">{entry.new_status}</span>
                  </p>
                  <p className="text-muted">
                    {formatDateTime(entry.changed_at)} &middot; {entry.changed_by_name}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </QueryBoundary>
      </div>
    </GlassCard>
  );
}

function PredictionCard({ application }: { application: ApplicationDetail }) {
  const { prediction } = application;
  const largest = Math.max(...application.top_features.map((item) => Math.abs(item.contribution)), 0);
  const counts = {
    required_matched: application.required_skills_matched.length,
    required_total: application.required_skills_matched.length + application.required_skills_missing.length,
    preferred_matched: application.preferred_skills_matched.length,
    preferred_total: application.preferred_skills_matched.length + application.preferred_skills_missing.length,
  };

  return (
    <GlassCard as="section">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <h2 className="card-title">Model prediction</h2>
        {prediction && (
          <p className="num text-[12.5px] text-muted">
            {prediction.model_version} &middot; {formatDate(prediction.computed_at)}
          </p>
        )}
      </div>
      <div className="mt-[14px]">
        <PredictionBadge prediction={prediction} message={application.prediction_message} hidePercent />
      </div>

      {prediction ? (
        <>
          <p className="mt-4 flex flex-wrap items-baseline gap-x-2">
            <span className="confidence-value">{formatPercent(prediction.probability)}</span>
            <span className="text-muted">confidence of a match</span>
          </p>
          <div aria-hidden="true" className="bar mt-4 h-[8px]">
            <div className="confidence-fill" style={{ width: formatPercent(prediction.probability) }} />
          </div>

          {application.top_features.length > 0 && (
            <>
              <h3 className="eyebrow mt-[20px]">Why this score</h3>
              <ul className="mt-3 space-y-[14px]">
                {application.top_features.map((item) => {
                  const isPositive = item.contribution >= 0;
                  // The largest effect fills most of the track, so the rows compare at a glance.
                  const width = largest > 0 ? (Math.abs(item.contribution) / largest) * 90 : 0;
                  return (
                    <li key={item.feature}>
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                        <span>
                          {formatFeatureName(item.feature)}{" "}
                          <span className="num text-muted">{formatFeatureValue(item.feature, item.value, counts)}</span>
                        </span>
                        <span className={`num whitespace-nowrap ${isPositive ? "text-ok" : "text-warn"}`}>
                          {formatPoints(item.contribution)}
                        </span>
                      </div>
                      <div aria-hidden="true" className="bar mt-[5px] h-[7px]">
                        <div className={isPositive ? "bar-fill-ok" : "bar-fill-warn"} style={{ width: `${width}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </>
      ) : (
        application.prediction_message && <p className="mt-3 text-muted">{application.prediction_message}</p>
      )}
      <p className="mt-[14px] text-muted">Advisory only. The model never changes the status.</p>
    </GlassCard>
  );
}

function SetStatusCard({ application, backTo }: { application: ApplicationDetail; backTo: string }) {
  const { changeStatus, isPending, message } = useStatusChange(application);
  const navigate = useNavigate();
  const deleteApplication = useDeleteApplication();
  const [deleteMessage, setDeleteMessage] = useState<string | null>(null);

  function handleDelete() {
    if (!window.confirm("Delete this application? The record stays in the database.")) return;
    setDeleteMessage(null);
    deleteApplication.mutate(
      { id: application.id, version: application.version },
      {
        onSuccess: () => navigate(backTo),
        onError: (error) => setDeleteMessage(error instanceof ApiError && error.isStale ? STALE_UPDATE_MESSAGE : error.message),
      },
    );
  }

  return (
    <GlassCard as="section">
      <h2 className="card-title">Set status</h2>
      <div role="group" aria-label="Set status" className="segmented mt-[14px]">
        {APPLICATION_STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            className="segment"
            aria-pressed={application.status === status}
            disabled={isPending}
            onClick={() => {
              if (application.status !== status) changeStatus(status);
            }}
          >
            {status}
          </button>
        ))}
      </div>
      <p className="mt-3 text-muted">Each change is saved with who made it and when.</p>
      {message && (
        <div className="mt-3">
          <WarningNotice message={message} />
        </div>
      )}
      {deleteMessage && (
        <div className="mt-3">
          <ErrorNotice message={deleteMessage} />
        </div>
      )}
      <div className="delete-row">
        <Button variant="ghost" className="btn-danger-text" disabled={deleteApplication.isPending} onClick={handleDelete}>
          Delete application
        </Button>
      </div>
    </GlassCard>
  );
}
