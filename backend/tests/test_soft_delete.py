"""Deleting hides a record from the API. The row and its history stay in the database."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Application, AuditLog, Candidate, Job


def _audit_actions(entity_type: str, entity_id: int) -> list[str]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AuditLog.action)
                .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
                .order_by(AuditLog.id)
            )
        )


def test_deleted_candidate_disappears_but_row_and_audit_remain(client, auth_headers, make_candidate):
    candidate = make_candidate(name="Deleted Person Zzq")

    response = client.delete(f"/api/candidates/{candidate['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert client.get(f"/api/candidates/{candidate['id']}", headers=auth_headers).status_code == 404
    with SessionLocal() as db:
        row = db.get(Candidate, candidate["id"])
        assert row is not None
        assert row.deleted_at is not None
    assert _audit_actions("candidate", candidate["id"]) == ["create", "delete"]


def test_deleting_a_candidate_also_hides_their_applications(client, auth_headers, make_application):
    application = make_application()

    client.delete(f"/api/candidates/{application['candidate_id']}", headers=auth_headers)

    assert client.get(f"/api/applications/{application['id']}", headers=auth_headers).status_code == 404
    with SessionLocal() as db:
        assert db.get(Application, application["id"]).deleted_at is not None
    assert _audit_actions("application", application["id"]) == ["create", "delete"]


def test_deleting_a_job_also_hides_its_applications(client, auth_headers, make_application):
    application = make_application()

    response = client.delete(f"/api/jobs/{application['job_id']}", headers=auth_headers)

    assert response.status_code == 204
    assert client.get(f"/api/jobs/{application['job_id']}", headers=auth_headers).status_code == 404
    assert client.get(f"/api/applications/{application['id']}", headers=auth_headers).status_code == 404
    with SessionLocal() as db:
        assert db.get(Job, application["job_id"]).deleted_at is not None
        assert db.get(Application, application["id"]).deleted_at is not None


def test_deleted_application_keeps_its_history(client, auth_headers, make_application):
    application = make_application()
    client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Shortlisted", "version": application["version"]},
        headers=auth_headers,
    )

    response = client.delete(f"/api/applications/{application['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert _audit_actions("application", application["id"]) == ["create", "status_change", "delete"]
    with SessionLocal() as db:
        assert len(db.get(Application, application["id"]).history) == 1


def test_deleting_twice_returns_404(client, auth_headers, make_candidate):
    candidate = make_candidate()
    client.delete(f"/api/candidates/{candidate['id']}", headers=auth_headers)
    assert client.delete(f"/api/candidates/{candidate['id']}", headers=auth_headers).status_code == 404


def test_cannot_update_or_apply_to_deleted_records(client, auth_headers, make_candidate, make_job):
    candidate = make_candidate()
    job = make_job()
    client.delete(f"/api/candidates/{candidate['id']}", headers=auth_headers)

    update = client.patch(
        f"/api/candidates/{candidate['id']}", json={"version": candidate["version"], "name": "X"}, headers=auth_headers
    )
    apply = client.post(
        "/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}, headers=auth_headers
    )

    assert update.status_code == 404
    assert apply.status_code == 404


def test_deleted_rows_keep_their_unique_values(client, auth_headers, make_candidate, make_application):
    """Reusing a deleted row's unique value would create a duplicate history. It gets a clear 409."""
    candidate = make_candidate()
    client.delete(f"/api/candidates/{candidate['id']}", headers=auth_headers)
    reused_email = client.post(
        "/api/candidates",
        json={"name": "New", "email": candidate["email"], "experience_years": 1, "skills": ["python"]},
        headers=auth_headers,
    )
    assert reused_email.status_code == 409
    assert "deleted" in reused_email.json()["detail"]

    application = make_application()
    client.delete(f"/api/applications/{application['id']}", headers=auth_headers)
    reapply = client.post(
        "/api/applications",
        json={"candidate_id": application["candidate_id"], "job_id": application["job_id"]},
        headers=auth_headers,
    )
    assert reapply.status_code == 409
    assert "deleted" in reapply.json()["detail"]
