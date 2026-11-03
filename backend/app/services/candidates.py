"""Business logic for candidates: create, update, soft delete."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Application, AuditAction, Candidate, CandidateSkill, User, utcnow
from app.schemas import CandidateCreate, CandidateUpdate
from app.services import skills as skill_service
from app.services.applications import soft_delete_applications_of
from app.services.audit import record_audit, snapshot_candidate
from app.services.common import assert_version, changed_fields, flush_checking_version, get_active
from app.services.predictions import refresh_predictions

# Only these change what the model sees, so only these trigger a rescore.
FIELDS_AFFECTING_PREDICTIONS = {"skills", "experience_years"}


def _duplicate_email_error(db: Session, email: str) -> AppError:
    existing = db.scalar(select(Candidate).where(Candidate.email == email))
    if existing is not None and existing.deleted_at is not None:
        detail = f"The email {email} belongs to a deleted candidate and can't be reused."
    else:
        detail = f"A candidate with the email {email} already exists."
    return AppError(409, "DUPLICATE_EMAIL", detail)


def set_candidate_skills(db: Session, candidate: Candidate, names: list[str]) -> None:
    """Make the candidate's skills match names, keeping links that are unchanged."""
    skills = skill_service.get_or_create_skills(db, names)
    current = {link.skill.name: link for link in candidate.skill_links}
    candidate.skill_links = [current.get(name) or CandidateSkill(skill=skills[name]) for name in names]


def create_candidate(db: Session, payload: CandidateCreate, user: User) -> Candidate:
    candidate = Candidate(
        name=payload.name,
        email=payload.email,
        experience_years=payload.experience_years,
        profile_summary=payload.profile_summary,
    )
    db.add(candidate)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _duplicate_email_error(db, payload.email) from None

    set_candidate_skills(db, candidate, payload.skills)
    db.flush()
    record_audit(db, "candidate", candidate.id, AuditAction.CREATE, None, snapshot_candidate(candidate), user.id)
    db.flush()
    return candidate


def update_candidate(db: Session, candidate_id: int, payload: CandidateUpdate, user: User) -> Candidate:
    candidate = get_active(db, Candidate, candidate_id, "candidate")
    assert_version(candidate, payload.version)
    before = snapshot_candidate(candidate)

    # Skills go first: creating a new skill flushes the session, and any email
    # conflict should surface at the flush below, where it is handled.
    if payload.skills is not None:
        set_candidate_skills(db, candidate, payload.skills)
    for field in ("name", "email", "experience_years", "profile_summary"):
        value = getattr(payload, field)
        if value is not None:
            setattr(candidate, field, value)

    changed = changed_fields(before, snapshot_candidate(candidate))
    if not changed:
        return candidate

    # Setting this forces an UPDATE (and a version bump) even when only skills
    # changed, since skills live in a separate table.
    candidate.updated_at = utcnow()
    try:
        flush_checking_version(db)
    except IntegrityError:
        db.rollback()
        raise _duplicate_email_error(db, payload.email) from None

    if changed & FIELDS_AFFECTING_PREDICTIONS:
        active = db.scalars(
            select(Application).where(Application.candidate_id == candidate.id, Application.deleted_at.is_(None))
        ).all()
        refresh_predictions(db, list(active))

    record_audit(db, "candidate", candidate.id, AuditAction.UPDATE, before, snapshot_candidate(candidate), user.id)
    db.flush()
    return candidate


def delete_candidate(db: Session, candidate_id: int, version: int | None, user: User) -> None:
    candidate = get_active(db, Candidate, candidate_id, "candidate")
    if version is not None:
        assert_version(candidate, version)

    before = snapshot_candidate(candidate)
    candidate.deleted_at = utcnow()
    flush_checking_version(db)
    record_audit(db, "candidate", candidate.id, AuditAction.DELETE, before, snapshot_candidate(candidate), user.id)
    soft_delete_applications_of(db, Application.candidate_id == candidate.id, user)
    db.flush()
