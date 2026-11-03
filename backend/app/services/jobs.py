"""Business logic for jobs: create, update, soft delete."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Application, AuditAction, Job, JobSkill, SkillKind, User, utcnow
from app.schemas import JobCreate, JobUpdate
from app.services import skills as skill_service
from app.services.applications import soft_delete_applications_of
from app.services.audit import record_audit, snapshot_job
from app.services.common import assert_version, changed_fields, flush_checking_version, get_active
from app.services.predictions import refresh_predictions

FIELDS_AFFECTING_PREDICTIONS = {"required_skills", "preferred_skills", "min_experience_years"}


def set_job_skills(db: Session, job: Job, required: list[str], preferred: list[str]) -> None:
    """Make the job's skills match the lists, keeping links that are unchanged."""
    kinds = {name: SkillKind.REQUIRED.value for name in required}
    kinds.update({name: SkillKind.PREFERRED.value for name in preferred})
    skills = skill_service.get_or_create_skills(db, kinds)

    current = {link.skill.name: link for link in job.skill_links}
    links = []
    for name, kind in kinds.items():
        link = current.get(name) or JobSkill(skill=skills[name], kind=kind)
        link.kind = kind
        links.append(link)
    job.skill_links = links


def create_job(db: Session, payload: JobCreate, user: User) -> Job:
    job = Job(
        title=payload.title,
        description=payload.description,
        min_experience_years=payload.min_experience_years,
    )
    db.add(job)
    db.flush()
    set_job_skills(db, job, payload.required_skills, payload.preferred_skills)
    db.flush()
    record_audit(db, "job", job.id, AuditAction.CREATE, None, snapshot_job(job), user.id)
    db.flush()
    return job


def update_job(db: Session, job_id: int, payload: JobUpdate, user: User) -> Job:
    job = get_active(db, Job, job_id, "job")
    assert_version(job, payload.version)
    before = snapshot_job(job)

    # Check the merged result: each list alone can be valid while the pair conflicts.
    required = payload.required_skills if payload.required_skills is not None else job.required_skill_names
    preferred = payload.preferred_skills if payload.preferred_skills is not None else job.preferred_skill_names
    overlap = sorted(set(required) & set(preferred))
    if overlap:
        raise AppError(422, "SKILL_CONFLICT", f"A skill can't be both required and preferred: {', '.join(overlap)}")

    if payload.required_skills is not None or payload.preferred_skills is not None:
        set_job_skills(db, job, required, preferred)
    for field in ("title", "description", "min_experience_years"):
        value = getattr(payload, field)
        if value is not None:
            setattr(job, field, value)

    changed = changed_fields(before, snapshot_job(job))
    if not changed:
        return job

    # Setting this forces an UPDATE (and a version bump) even when only skills changed.
    job.updated_at = utcnow()
    flush_checking_version(db)

    if changed & FIELDS_AFFECTING_PREDICTIONS:
        active = db.scalars(select(Application).where(Application.job_id == job.id, Application.deleted_at.is_(None))).all()
        refresh_predictions(db, list(active))

    record_audit(db, "job", job.id, AuditAction.UPDATE, before, snapshot_job(job), user.id)
    db.flush()
    return job


def delete_job(db: Session, job_id: int, version: int | None, user: User) -> None:
    job = get_active(db, Job, job_id, "job")
    if version is not None:
        assert_version(job, version)

    before = snapshot_job(job)
    job.deleted_at = utcnow()
    flush_checking_version(db)
    record_audit(db, "job", job.id, AuditAction.DELETE, before, snapshot_job(job), user.id)
    soft_delete_applications_of(db, Application.job_id == job.id, user)
    db.flush()
