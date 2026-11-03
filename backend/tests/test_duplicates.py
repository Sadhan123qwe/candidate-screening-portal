"""Duplicates are refused by database constraints and reported as a readable 409."""

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Application, Candidate


def test_same_application_twice_returns_409_and_one_row(client, auth_headers, make_job, make_candidate):
    body = {"candidate_id": make_candidate()["id"], "job_id": make_job()["id"]}

    first = client.post("/api/applications", json=body, headers=auth_headers)
    second = client.post("/api/applications", json=body, headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "DUPLICATE_APPLICATION"
    assert "already applied" in second.json()["detail"]

    with SessionLocal() as db:
        rows = db.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.candidate_id == body["candidate_id"], Application.job_id == body["job_id"])
        )
    assert rows == 1


def test_duplicate_email_returns_409_regardless_of_case(client, auth_headers, make_candidate):
    candidate = make_candidate(email="Duplicate.Check@Example.com")
    assert candidate["email"] == "duplicate.check@example.com"

    response = client.post(
        "/api/candidates",
        json={"name": "Other", "email": "DUPLICATE.CHECK@example.com", "experience_years": 1, "skills": ["python"]},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DUPLICATE_EMAIL"
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count()).select_from(Candidate).where(Candidate.email == "duplicate.check@example.com")
        ) == 1


def test_changing_email_to_one_in_use_returns_409(client, auth_headers, make_candidate):
    first = make_candidate()
    second = make_candidate()

    response = client.patch(
        f"/api/candidates/{second['id']}",
        json={"version": second["version"], "email": first["email"]},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DUPLICATE_EMAIL"
    reread = client.get(f"/api/candidates/{second['id']}", headers=auth_headers).json()
    assert reread["email"] == second["email"]
    assert reread["version"] == second["version"]
