"""Find-or-create for the shared skills table."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.models import Skill

# Both dialects offer the same ON CONFLICT API, but through different insert functions.
_INSERT_BY_DIALECT = {"sqlite": sqlite.insert, "postgresql": postgresql.insert}


def get_or_create_skills(db: Session, names: Iterable[str]) -> dict[str, Skill]:
    """Return a Skill for every name, creating any that don't exist yet.

    ON CONFLICT DO NOTHING makes this safe when two requests add the same new
    skill at once: the second insert does nothing instead of failing the request.
    """
    wanted = set(names)
    existing = db.scalars(select(Skill).where(Skill.name.in_(wanted))).all()
    missing = wanted - {skill.name for skill in existing}

    if missing:
        insert = _INSERT_BY_DIALECT[db.get_bind().dialect.name]
        db.execute(
            insert(Skill.__table__)
            .values([{"name": name} for name in sorted(missing)])
            .on_conflict_do_nothing(index_elements=["name"])
        )
        existing = db.scalars(select(Skill).where(Skill.name.in_(wanted))).all()

    return {skill.name: skill for skill in existing}
