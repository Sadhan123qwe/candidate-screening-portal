"""The audit trail: one row per write, saved in the same transaction as that write.

Sharing the transaction means the two succeed or fail together, so a rolled-back
request leaves no audit row, and a saved change always has one.
"""

from sqlalchemy.orm import Session

from app.models import Application, AuditAction, AuditLog, Candidate, Job


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def snapshot_job(job: Job) -> dict:
    return {
        "id": job.id,
        "external_ref": job.external_ref,
        "title": job.title,
        "description": job.description,
        "min_experience_years": job.min_experience_years,
        "required_skills": job.required_skill_names,
        "preferred_skills": job.preferred_skill_names,
        "version": job.version,
        "deleted_at": _iso(job.deleted_at),
    }


def snapshot_candidate(candidate: Candidate) -> dict:
    return {
        "id": candidate.id,
        "external_ref": candidate.external_ref,
        "name": candidate.name,
        "email": candidate.email,
        "experience_years": candidate.experience_years,
        "profile_summary": candidate.profile_summary,
        "skills": candidate.skill_names,
        "version": candidate.version,
        "deleted_at": _iso(candidate.deleted_at),
    }


def snapshot_application(application: Application) -> dict:
    return {
        "id": application.id,
        "external_ref": application.external_ref,
        "candidate_id": application.candidate_id,
        "job_id": application.job_id,
        "status": application.status,
        "version": application.version,
        "deleted_at": _iso(application.deleted_at),
    }


def record_audit(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    before: dict | None,
    after: dict | None,
    user_id: int | None,
) -> None:
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action.value,
            before_json=before,
            after_json=after,
            user_id=user_id,
        )
    )
