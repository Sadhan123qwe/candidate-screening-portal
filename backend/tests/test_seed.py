"""Seeding is repeatable and never overwrites a recruiter's work."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import build_engine
from app.models import Application, AuditLog, Base, Candidate, Job, Prediction, Skill, User, utcnow
from app.services.startup import run_migrations
from scripts.seed import seed_database


@pytest.fixture
def seed_engine(tmp_path):
    """A separate empty database, so these tests can count rows exactly."""
    engine = build_engine(f"sqlite:///{(tmp_path / 'seed.db').as_posix()}")
    run_migrations(engine)
    yield engine
    engine.dispose()


def _run_seed(engine):
    with Session(engine) as db, db.begin():
        return seed_database(db)


def _counts(engine) -> dict[str, int]:
    with Session(engine) as db:
        return {table.name: db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}


def test_first_seed_imports_expected_counts(seed_engine):
    _run_seed(seed_engine)
    counts = _counts(seed_engine)

    assert counts["candidates"] == 250
    assert counts["jobs"] == 10
    assert counts["applications"] == 500
    assert counts["predictions"] == 500
    assert counts["users"] == 1
    with Session(seed_engine) as db:
        statuses = set(db.scalars(select(Application.status)))
    assert statuses == {"Applied"}


def test_seeding_twice_changes_nothing(seed_engine):
    _run_seed(seed_engine)
    before = _counts(seed_engine)

    summary = _run_seed(seed_engine)

    assert _counts(seed_engine) == before
    assert summary["applications inserted"] == 0
    assert summary["candidates inserted"] == 0
    assert summary["jobs inserted"] == 0


def test_reseed_preserves_recruiter_changes(seed_engine):
    _run_seed(seed_engine)
    with Session(seed_engine) as db, db.begin():
        application = db.scalar(select(Application).where(Application.external_ref == "A0001"))
        application.status = "Shortlisted"
        candidate = db.scalar(select(Candidate).where(Candidate.external_ref == "C0001"))
        candidate.name = "Renamed By Recruiter"
        job = db.scalar(select(Job).where(Job.external_ref == "J001"))
        job.title = "Retitled By Recruiter"

    _run_seed(seed_engine)

    with Session(seed_engine) as db:
        assert db.scalar(select(Application.status).where(Application.external_ref == "A0001")) == "Shortlisted"
        assert db.scalar(select(Candidate.name).where(Candidate.external_ref == "C0001")) == "Renamed By Recruiter"
        assert db.scalar(select(Job.title).where(Job.external_ref == "J001")) == "Retitled By Recruiter"


def test_reseed_does_not_resurrect_soft_deleted_rows(seed_engine):
    _run_seed(seed_engine)
    with Session(seed_engine) as db, db.begin():
        application = db.scalar(select(Application).where(Application.external_ref == "A0001"))
        application.deleted_at = utcnow()

    _run_seed(seed_engine)

    with Session(seed_engine) as db:
        restored = db.scalar(select(Application).where(Application.external_ref == "A0001"))
        assert restored.deleted_at is not None
        assert db.scalar(select(func.count()).select_from(Application)) == 500


def test_seed_skips_a_candidate_whose_email_a_recruiter_already_used(seed_engine):
    with Session(seed_engine) as db, db.begin():
        db.add(Candidate(name="Added In UI", email="candidate001@example.com", experience_years=9))

    summary = _run_seed(seed_engine)

    assert summary["candidates skipped (email already in use)"] == 1
    with Session(seed_engine) as db:
        kept = db.scalar(select(Candidate).where(Candidate.email == "candidate001@example.com"))
        assert kept.name == "Added In UI"
        assert kept.experience_years == 9


def test_failed_seed_leaves_database_untouched(seed_engine, monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("Simulated failure at the last step")

    monkeypatch.setattr("scripts.seed.refresh_stale_predictions", fail)

    with pytest.raises(RuntimeError):
        _run_seed(seed_engine)

    assert set(_counts(seed_engine).values()) == {0}


def test_every_seeded_row_has_an_audit_row_and_no_user(seed_engine):
    _run_seed(seed_engine)
    with Session(seed_engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 760
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.user_id.is_not(None))) == 0


def test_demo_user_and_skills_are_stored_lowercase(seed_engine):
    _run_seed(seed_engine)
    with Session(seed_engine) as db:
        assert db.scalar(select(User.email)) == "recruiter@demo.com"
        assert all(name == name.lower() for name in db.scalars(select(Skill.name)))
        assert all(0 <= value <= 1 for value in db.scalars(select(Prediction.probability)))
