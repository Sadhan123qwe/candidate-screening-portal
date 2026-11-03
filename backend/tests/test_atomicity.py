"""A request either saves everything or nothing, and success means it is already committed."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AuditLog, Candidate, CandidateSkill


def _candidate_body() -> dict:
    return {
        "name": "Atomic Test",
        "email": f"atomic-{uuid.uuid4().hex[:10]}@example.com",
        "experience_years": 1,
        "skills": ["python"],
    }


def _table_counts() -> tuple[int, int, int]:
    with SessionLocal() as db:
        return (
            db.scalar(select(func.count()).select_from(Candidate)),
            db.scalar(select(func.count()).select_from(CandidateSkill)),
            db.scalar(select(func.count()).select_from(AuditLog)),
        )


def test_error_halfway_through_candidate_creation_saves_nothing(client, auth_headers, monkeypatch):
    before = _table_counts()

    # The candidate row has been flushed by this point, so this really is halfway.
    def fail(*_args, **_kwargs):
        raise RuntimeError("Simulated failure during skill insert")

    monkeypatch.setattr("app.services.skills.get_or_create_skills", fail)
    body = _candidate_body()

    response = client.post("/api/candidates", json=body, headers=auth_headers)

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert _table_counts() == before
    with SessionLocal() as db:
        assert db.scalar(select(Candidate).where(Candidate.email == body["email"])) is None


def test_error_when_writing_audit_row_rolls_back_the_change(client, auth_headers, monkeypatch):
    before = _table_counts()

    def fail(*_args, **_kwargs):
        raise RuntimeError("Simulated audit failure")

    monkeypatch.setattr("app.services.candidates.record_audit", fail)

    response = client.post("/api/candidates", json=_candidate_body(), headers=auth_headers)

    assert response.status_code == 500
    assert _table_counts() == before


def test_failed_commit_returns_an_error_instead_of_success(client, auth_headers, monkeypatch):
    """Proves the commit runs before the response is sent.

    With FastAPI's default dependency scope this test fails: the client gets a 201
    for data that was never saved.
    """
    before = _table_counts()

    def fail(_session):
        raise RuntimeError("Simulated disk failure at commit")

    monkeypatch.setattr(Session, "commit", fail)

    response = client.post("/api/candidates", json=_candidate_body(), headers=auth_headers)

    monkeypatch.undo()
    assert response.status_code == 500
    assert _table_counts() == before
