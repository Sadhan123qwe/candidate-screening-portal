"""Turn database rows into API response models.

Routers call these before returning, so the data is read while the session is open
and any problem surfaces before the transaction commits.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml import predictor as predictor_module
from app.models import Application, Candidate, Job, Prediction, PredictionLabel, StatusHistory
from app.schemas import (
    ApplicationCounts,
    ApplicationDetail,
    ApplicationOut,
    CandidateDetail,
    CandidateOut,
    FeatureContributionOut,
    JobOut,
    JobSummaryOut,
    PredictionOut,
    StatusHistoryOut,
)
from app.services.predictions import features_for

NOT_COMPUTED_MESSAGE = "No prediction has been computed for this application yet."


def _prediction_fields(application: Application) -> tuple[PredictionOut | None, str | None]:
    if not predictor_module.get_predictor().available:
        return None, predictor_module.UNAVAILABLE_MESSAGE
    stored = application.prediction
    if stored is None:
        return None, NOT_COMPUTED_MESSAGE
    prediction = PredictionOut(
        label=stored.label,
        probability=stored.probability,
        model_version=stored.model_version,
        computed_at=stored.computed_at,
    )
    return prediction, None


def _application_fields(application: Application) -> dict:
    prediction, message = _prediction_fields(application)
    candidate, job = application.candidate, application.job
    required = job.required_skill_names
    candidate_skills = set(candidate.skill_names)
    return {
        "id": application.id,
        "candidate_id": application.candidate_id,
        "candidate_name": candidate.name,
        "candidate_email": candidate.email,
        "candidate_experience_years": candidate.experience_years,
        "job_id": application.job_id,
        "job_title": job.title,
        "required_matched": sum(skill in candidate_skills for skill in required),
        "required_total": len(required),
        "status": application.status,
        "version": application.version,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "prediction": prediction,
        "prediction_message": message,
    }


def to_application_out(application: Application) -> ApplicationOut:
    return ApplicationOut(**_application_fields(application))


def to_application_detail(application: Application) -> ApplicationDetail:
    predictor = predictor_module.get_predictor()
    contributions = predictor.explain(features_for(application)) if predictor.available else []
    candidate, job = application.candidate, application.job
    candidate_skills = candidate.skill_names
    required = job.required_skill_names
    preferred = job.preferred_skill_names
    return ApplicationDetail(
        **_application_fields(application),
        top_features=[
            FeatureContributionOut(feature=item.feature, value=item.value, contribution=item.contribution)
            for item in contributions
        ],
        candidate_profile_summary=candidate.profile_summary,
        job_min_experience_years=job.min_experience_years,
        experience_gap=candidate.experience_years - job.min_experience_years,
        required_skills_matched=[skill for skill in required if skill in candidate_skills],
        required_skills_missing=[skill for skill in required if skill not in candidate_skills],
        preferred_skills_matched=[skill for skill in preferred if skill in candidate_skills],
        preferred_skills_missing=[skill for skill in preferred if skill not in candidate_skills],
        other_candidate_skills=[skill for skill in candidate_skills if skill not in required and skill not in preferred],
        imported_from_dataset=application.external_ref is not None,
    )


def _candidate_fields(candidate: Candidate, application_count: int) -> dict:
    return {
        "id": candidate.id,
        "external_ref": candidate.external_ref,
        "name": candidate.name,
        "email": candidate.email,
        "experience_years": candidate.experience_years,
        "profile_summary": candidate.profile_summary,
        "skills": candidate.skill_names,
        "version": candidate.version,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
        "application_count": application_count,
    }


def to_candidate_out(candidate: Candidate, application_count: int = 0) -> CandidateOut:
    return CandidateOut(**_candidate_fields(candidate, application_count))


def to_candidate_detail(db: Session, candidate: Candidate) -> CandidateDetail:
    applications = db.scalars(
        select(Application)
        .where(Application.candidate_id == candidate.id, Application.deleted_at.is_(None))
        .order_by(Application.created_at.desc(), Application.id.desc())
    ).all()
    return CandidateDetail(
        **_candidate_fields(candidate, len(applications)),
        applications=[to_application_out(application) for application in applications],
    )


def application_counts_by_job(db: Session) -> dict[int, ApplicationCounts]:
    """One grouped query, so a list of jobs doesn't run a count per job."""
    rows = db.execute(
        select(Application.job_id, Application.status, func.count())
        .where(Application.deleted_at.is_(None))
        .group_by(Application.job_id, Application.status)
    ).all()
    counts: dict[int, ApplicationCounts] = {}
    for job_id, status, count in rows:
        setattr(counts.setdefault(job_id, ApplicationCounts()), status, count)
    return counts


def application_counts_by_candidate(db: Session) -> dict[int, int]:
    """One grouped query, so a list of candidates doesn't run a count per candidate."""
    rows = db.execute(
        select(Application.candidate_id, func.count())
        .where(Application.deleted_at.is_(None))
        .group_by(Application.candidate_id)
    ).all()
    return {candidate_id: count for candidate_id, count in rows}


def job_summaries(db: Session, jobs: list[Job]) -> list[JobSummaryOut]:
    """Status and prediction counts for each job, from two grouped queries in total."""
    counts = application_counts_by_job(db)
    model_available = predictor_module.get_predictor().available
    matches = dict(
        db.execute(
            select(Application.job_id, func.count())
            .join(Application.prediction)
            .where(Application.deleted_at.is_(None), Prediction.label == PredictionLabel.POTENTIAL_MATCH.value)
            .group_by(Application.job_id)
        ).all()
    )
    summaries = []
    for job in jobs:
        job_counts = counts.get(job.id, ApplicationCounts())
        summaries.append(
            JobSummaryOut(
                job_id=job.id,
                applied=job_counts.Applied,
                shortlisted=job_counts.Shortlisted,
                rejected=job_counts.Rejected,
                potential_match=matches.get(job.id, 0) if model_available else None,
            )
        )
    return summaries


def to_job_out(job: Job, counts: ApplicationCounts | None = None) -> JobOut:
    return JobOut(
        id=job.id,
        external_ref=job.external_ref,
        title=job.title,
        description=job.description,
        min_experience_years=job.min_experience_years,
        required_skills=job.required_skill_names,
        preferred_skills=job.preferred_skill_names,
        version=job.version,
        created_at=job.created_at,
        updated_at=job.updated_at,
        application_counts=counts or ApplicationCounts(),
    )


def to_status_history_out(entry: StatusHistory) -> StatusHistoryOut:
    return StatusHistoryOut(
        id=entry.id,
        old_status=entry.old_status,
        new_status=entry.new_status,
        changed_by_user_id=entry.changed_by_user_id,
        changed_by_name=entry.changed_by.full_name,
        changed_at=entry.changed_at,
    )
