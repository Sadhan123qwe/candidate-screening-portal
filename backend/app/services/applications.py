"""Business logic for applications: create, change status, soft delete."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, not_found
from app.models import Application, ApplicationStatus, AuditAction, Candidate, Job, StatusHistory, User, utcnow
from app.services.audit import record_audit, snapshot_application
from app.services.common import assert_version, flush_checking_version, get_active
from app.services.predictions import refresh_predictions


def _duplicate_application_error(db: Session, candidate_id: int, job_id: int) -> AppError:
    existing = db.scalar(
        select(Application).where(Application.candidate_id == candidate_id, Application.job_id == job_id)
    )
    if existing is not None and existing.deleted_at is not None:
        detail = "This candidate previously applied to this job, and that application was deleted."
    else:
        detail = "This candidate has already applied to this job."
    return AppError(409, "DUPLICATE_APPLICATION", detail)


def create_application(db: Session, candidate_id: int, job_id: int, user: User) -> Application:
    candidate = get_active(db, Candidate, candidate_id, "candidate")
    job = get_active(db, Job, job_id, "job")

    application = Application(candidate=candidate, job=job, status=ApplicationStatus.APPLIED.value)
    db.add(application)
    try:
        db.flush()
    except IntegrityError:
        # There is deliberately no "does it exist?" check before the insert. Two
        # simultaneous requests could both pass one. The database decides instead.
        db.rollback()
        raise _duplicate_application_error(db, candidate_id, job_id) from None

    # The checks above ran before this transaction held a lock, so a parent could have
    # been deleted since. Re-read with the lock held. FOR UPDATE makes a concurrent
    # delete wait on PostgreSQL, and SQLite ignores it because the insert already
    # holds the single write lock.
    for parent, label in ((candidate, "candidate"), (job, "job")):
        db.refresh(parent, with_for_update=True)
        if parent.deleted_at is not None:
            raise not_found(label)

    refresh_predictions(db, [application])
    record_audit(
        db, "application", application.id, AuditAction.CREATE, None, snapshot_application(application), user.id
    )
    db.flush()
    return application


def change_status(db: Session, application_id: int, new_status: ApplicationStatus, version: int, user: User) -> Application:
    application = get_active(db, Application, application_id, "application")
    assert_version(application, version)

    old_status = application.status
    if old_status == new_status.value:
        return application  # Nothing changed, so there is nothing to record.

    before = snapshot_application(application)
    application.status = new_status.value
    flush_checking_version(db)

    db.add(
        StatusHistory(
            application_id=application.id,
            old_status=old_status,
            new_status=new_status.value,
            changed_by_user_id=user.id,
        )
    )
    record_audit(
        db, "application", application.id, AuditAction.STATUS_CHANGE, before, snapshot_application(application), user.id
    )
    db.flush()
    return application


def soft_delete_application(db: Session, application: Application, user: User) -> None:
    before = snapshot_application(application)
    application.deleted_at = utcnow()
    flush_checking_version(db)
    record_audit(
        db, "application", application.id, AuditAction.DELETE, before, snapshot_application(application), user.id
    )


def delete_application(db: Session, application_id: int, version: int | None, user: User) -> None:
    application = get_active(db, Application, application_id, "application")
    if version is not None:
        assert_version(application, version)
    soft_delete_application(db, application, user)
    db.flush()


def soft_delete_applications_of(db: Session, parent_filter, user: User) -> None:
    """Remove a deleted candidate's or job's applications from view, with audit rows.

    Called after the parent's delete is flushed, so this transaction holds the write
    lock and can't miss an application committed a moment earlier.
    """
    active = db.scalars(select(Application).where(parent_filter, Application.deleted_at.is_(None))).all()
    for application in active:
        soft_delete_application(db, application, user)
