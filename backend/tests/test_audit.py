"""Every write leaves exactly one audit row with correct values. A rollback leaves none."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import AuditLog, User


def _audit_rows(entity_type: str, entity_id: int) -> list[AuditLog]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
                .order_by(AuditLog.id)
            )
        )


def _total_audit_rows() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(AuditLog))


def _demo_user_id() -> int:
    with SessionLocal() as db:
        return db.scalar(select(User.id).where(User.email == "recruiter@demo.com"))


def test_candidate_create_and_update_add_one_row_each(client, auth_headers, make_candidate):
    candidate = make_candidate(name="Before Name")

    rows = _audit_rows("candidate", candidate["id"])
    assert [row.action for row in rows] == ["create"]
    assert rows[0].before_json is None
    assert rows[0].after_json["name"] == "Before Name"
    assert rows[0].user_id == _demo_user_id()
    assert rows[0].created_at.utcoffset().total_seconds() == 0

    client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "name": "After Name"},
        headers=auth_headers,
    )

    rows = _audit_rows("candidate", candidate["id"])
    assert [row.action for row in rows] == ["create", "update"]
    assert rows[1].before_json["name"] == "Before Name"
    assert rows[1].after_json["name"] == "After Name"
    assert rows[1].after_json["version"] == candidate["version"] + 1


def test_job_create_and_update_add_one_row_each(client, auth_headers, make_job):
    job = make_job(required_skills=["python"], preferred_skills=[])

    client.patch(
        f"/api/jobs/{job['id']}",
        json={"version": job["version"], "required_skills": ["python", "sql"]},
        headers=auth_headers,
    )

    rows = _audit_rows("job", job["id"])
    assert [row.action for row in rows] == ["create", "update"]
    assert rows[1].before_json["required_skills"] == ["python"]
    assert rows[1].after_json["required_skills"] == ["python", "sql"]


def test_application_create_and_status_change_add_one_row_each(client, auth_headers, make_application):
    application = make_application()

    client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Rejected", "version": application["version"]},
        headers=auth_headers,
    )

    rows = _audit_rows("application", application["id"])
    assert [row.action for row in rows] == ["create", "status_change"]
    assert rows[1].before_json["status"] == "Applied"
    assert rows[1].after_json["status"] == "Rejected"


def test_update_that_changes_nothing_adds_no_audit_row(client, auth_headers, make_candidate):
    candidate = make_candidate()

    response = client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "name": candidate["name"]},
        headers=auth_headers,
    )

    assert response.json()["version"] == candidate["version"]
    assert len(_audit_rows("candidate", candidate["id"])) == 1


def test_setting_the_same_status_adds_no_audit_or_history_row(client, auth_headers, make_application):
    application = make_application()

    response = client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Applied", "version": application["version"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(_audit_rows("application", application["id"])) == 1
    assert client.get(f"/api/applications/{application['id']}/history", headers=auth_headers).json() == []


def test_rejected_requests_add_no_audit_rows(client, auth_headers, make_application):
    application = make_application()
    url = f"/api/applications/{application['id']}/status"
    before = _total_audit_rows()

    stale = client.patch(url, json={"status": "Rejected", "version": 999}, headers=auth_headers)
    invalid = client.patch(url, json={"status": "Hired", "version": application["version"]}, headers=auth_headers)
    duplicate = client.post(
        "/api/applications",
        json={"candidate_id": application["candidate_id"], "job_id": application["job_id"]},
        headers=auth_headers,
    )

    assert (stale.status_code, invalid.status_code, duplicate.status_code) == (409, 422, 409)
    assert _total_audit_rows() == before


def test_rolled_back_request_adds_no_audit_row(client, auth_headers, make_candidate, monkeypatch):
    """The audit row is written, and then a later failure must take it back too."""
    candidate = make_candidate()
    before = _total_audit_rows()

    calls = {"count": 0}
    real_flush = Session.flush

    def fail_after_audit_is_added(self, *args, **kwargs):
        # Only fail once the audit row is pending, which proves it isn't saved on its own.
        if any(isinstance(pending, AuditLog) for pending in self.new):
            calls["count"] += 1
            raise RuntimeError("Simulated failure after the audit row was added")
        return real_flush(self, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", fail_after_audit_is_added)

    response = client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "name": "Should Not Save"},
        headers=auth_headers,
    )

    monkeypatch.undo()
    assert calls["count"] == 1
    assert response.status_code == 500
    assert _total_audit_rows() == before
    assert client.get(f"/api/candidates/{candidate['id']}", headers=auth_headers).json()["name"] == candidate["name"]
