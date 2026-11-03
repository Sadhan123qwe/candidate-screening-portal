"""Small helpers shared by the services that write to the database."""

from typing import TypeVar

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import StaleDataError

from app.errors import not_found, stale_update
from app.models import Application, Candidate, Job, utcnow

SoftDeletable = TypeVar("SoftDeletable", Application, Candidate, Job)


def get_active(db: Session, model: type[SoftDeletable], entity_id: int, label: str) -> SoftDeletable:
    """Fetch a row, treating a soft-deleted one exactly like a missing one."""
    entity = db.get(model, entity_id)
    if entity is None or entity.deleted_at is not None:
        raise not_found(label)
    return entity


def assert_version(entity: Application | Candidate | Job, client_version: int) -> None:
    """Refuse an update that was based on an older copy of the row."""
    if entity.version != client_version:
        raise stale_update()


def flush_checking_version(db: Session) -> None:
    """Send pending changes now, so a lost race becomes a clean 409.

    assert_version catches a client holding an old copy. This catches the narrower
    case of two requests that both passed that check at the same moment: the
    database's WHERE version = ? matches only one, and SQLAlchemy raises for the other.
    """
    try:
        db.flush()
    except StaleDataError:
        db.rollback()
        raise stale_update() from None


def mark_row_changed(entity: Candidate | Job) -> None:
    """Force an UPDATE, and so a version bump, even if no column on this row changed.

    Skills live in separate tables, so editing only skills wouldn't touch the parent
    row, and a concurrent edit could then overwrite it. Setting updated_at isn't enough
    alone: the clock can return the same value twice in quick succession (Windows' clock
    ticks coarsely), and SQLAlchemy skips the UPDATE when a value is unchanged.
    """
    entity.updated_at = utcnow()
    flag_modified(entity, "updated_at")


def changed_fields(before: dict, after: dict) -> set[str]:
    return {key for key in after if before.get(key) != after[key]}
