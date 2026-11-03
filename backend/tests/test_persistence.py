"""Data lives in the file, not in the process. scripts/persistence_check.py does the full crash test."""

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import build_engine, engine
from app.models import Application, Job


def test_data_survives_disposing_the_engine(make_application):
    created = make_application()

    # Close every pooled connection, then read through a brand new engine.
    engine.dispose()
    fresh_engine = build_engine(engine.url)
    try:
        with Session(fresh_engine) as db:
            application = db.get(Application, created["id"])
            job = db.get(Job, created["job_id"])
            assert application is not None
            assert application.status == "Applied"
            assert job.title == created["job_title"]
    finally:
        fresh_engine.dispose()


def test_timestamps_are_timezone_aware_utc(make_application):
    created = make_application()

    with Session(engine) as db:
        application = db.scalar(select(Application).where(Application.id == created["id"]))

    assert application.created_at.tzinfo == timezone.utc
    # The API must send an explicit UTC marker, or browsers would read it as local time.
    assert created["created_at"].endswith("Z")


def test_client_cannot_set_timestamps(client, auth_headers):
    response = client.post(
        "/api/jobs",
        json={"title": "Backdated", "required_skills": ["python"], "created_at": "2001-01-01T00:00:00Z"},
        headers=auth_headers,
    )
    assert response.status_code == 422
