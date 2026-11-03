"""The database constraints themselves, independent of the API's validation."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import build_engine
from app.models import Application, Candidate, Job
from app.services.startup import run_migrations


@pytest.fixture
def engine(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'schema.db').as_posix()}")
    run_migrations(engine)
    yield engine
    engine.dispose()


def test_migrations_match_the_models(engine):
    """Fails if someone changes models.py and forgets to write a migration."""
    config = Config(BACKEND_DIR / "alembic.ini")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)


def test_foreign_keys_are_enforced(engine):
    # Python's sqlite3 reports this as OperationalError when the INSERT uses RETURNING.
    # Either way the point stands: the row is refused.
    with pytest.raises((IntegrityError, OperationalError), match="FOREIGN KEY"):
        with Session(engine) as db, db.begin():
            db.add(Application(candidate_id=999_999, job_id=999_999))


def test_database_rejects_negative_experience(engine):
    with pytest.raises(IntegrityError):
        with Session(engine) as db, db.begin():
            db.add(Candidate(name="N", email="negative@example.com", experience_years=-1))


def test_database_rejects_unknown_status(engine):
    with Session(engine) as db, db.begin():
        job = Job(title="J")
        candidate = Candidate(name="N", email="status@example.com", experience_years=0)
        db.add_all([job, candidate])
        db.flush()
        job_id, candidate_id = job.id, candidate.id

    with pytest.raises(IntegrityError):
        with Session(engine) as db, db.begin():
            db.add(Application(candidate_id=candidate_id, job_id=job_id, status="Hired"))


def test_filter_columns_are_indexed(engine):
    inspector = inspect(engine)
    application_indexes = {tuple(index["column_names"]) for index in inspector.get_indexes("applications")}
    candidate_indexes = {tuple(index["column_names"]) for index in inspector.get_indexes("candidates")}

    assert ("job_id",) in application_indexes
    assert ("status",) in application_indexes
    assert ("email",) in candidate_indexes
