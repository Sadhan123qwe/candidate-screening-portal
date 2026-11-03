"""Turn database rows into API response models.

Routers call these before returning, so the data is read while the session is open
and any problem surfaces before the transaction commits.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml import predictor as predictor_module
from app.models import Application, Candidate, Job, StatusHistory
from app.schemas import (
    ApplicationCounts,
    ApplicationDetail,
    ApplicationOut,
    CandidateDetail,
    CandidateOut,
    FeatureContributionOut,
    JobOut,
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
    return {
        "id": application.id,
        "candidate_id": application.candidate_id,
        "candidate_name": application.candidate.name,
        "job_id": application.job_id,
        "job_title": application.job.title,
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
    return ApplicationDetail(
        **_application_fields(application),
        candidate_email=application.candidate.email,
        top_features=[
            FeatureContributionOut(feature=item.feature, value=item.value, contribution=item.contribution)
            for item in contributions
        ],
    )


def _candidate_fields(candidate: Candidate) -> dict:
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
    }


def to_candidate_out(candidate: Candidate) -> CandidateOut:
    return CandidateOut(**_candidate_fields(candidate))


def to_candidate_detail(db: Session, candidate: Candidate) -> CandidateDetail:
    applications = db.scalars(
        select(Application)
        .where(Application.candidate_id == candidate.id, Application.deleted_at.is_(None))
        .order_by(Application.created_at.desc(), Application.id.desc())
    ).all()
    return CandidateDetail(
        **_candidate_fields(candidate),
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
