"""Status changes write a history row and are the only way a status moves."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import StatusHistory, User


def test_status_update_writes_status_history(client, auth_headers, make_application):
    application = make_application()

    response = client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Shortlisted", "version": application["version"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Shortlisted"

    history = client.get(f"/api/applications/{application['id']}/history", headers=auth_headers).json()
    assert len(history) == 1
    assert history[0]["old_status"] == "Applied"
    assert history[0]["new_status"] == "Shortlisted"
    assert history[0]["changed_by_name"] == "Demo Recruiter"
    assert history[0]["changed_at"].endswith("Z")

    with SessionLocal() as db:
        demo_user_id = db.scalar(select(User.id).where(User.email == "recruiter@demo.com"))
        row = db.scalar(select(StatusHistory).where(StatusHistory.application_id == application["id"]))
    assert row.changed_by_user_id == demo_user_id


def test_history_is_a_timeline_in_order(client, auth_headers, make_application):
    application = make_application()
    url = f"/api/applications/{application['id']}/status"
    version = application["version"]

    for status in ("Shortlisted", "Rejected", "Applied"):
        version = client.patch(url, json={"status": status, "version": version}, headers=auth_headers).json()["version"]

    history = client.get(f"/api/applications/{application['id']}/history", headers=auth_headers).json()
    assert [(entry["old_status"], entry["new_status"]) for entry in history] == [
        ("Applied", "Shortlisted"),
        ("Shortlisted", "Rejected"),
        ("Rejected", "Applied"),
    ]


def test_new_applications_start_as_applied_whatever_the_model_says(make_application):
    application = make_application()
    assert application["status"] == "Applied"
    assert application["prediction"] is not None


def test_rescoring_never_changes_status(client, auth_headers, make_application):
    application = make_application()
    client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Rejected", "version": application["version"]},
        headers=auth_headers,
    )
    candidate = client.get(f"/api/candidates/{application['candidate_id']}", headers=auth_headers).json()

    # This would flip the score, but a recruiter's decision must stay as it is.
    client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "skills": ["python", "sql", "docker", "git"]},
        headers=auth_headers,
    )

    assert client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()["status"] == "Rejected"
