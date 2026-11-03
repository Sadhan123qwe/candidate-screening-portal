"""Lists, search, filters and pagination, plus the health and metrics endpoints."""

import uuid


def test_applications_are_paginated(client, auth_headers):
    first = client.get("/api/applications", params={"page": 1, "page_size": 10}, headers=auth_headers).json()
    second = client.get("/api/applications", params={"page": 2, "page_size": 10}, headers=auth_headers).json()

    assert len(first["items"]) == 10
    assert len(second["items"]) == 10
    assert first["total"] >= 500
    assert not {item["id"] for item in first["items"]} & {item["id"] for item in second["items"]}


def test_application_rows_have_what_the_table_needs(client, auth_headers):
    row = client.get("/api/applications", params={"page_size": 1}, headers=auth_headers).json()["items"][0]
    for field in ("candidate_name", "job_title", "status", "version", "created_at", "prediction"):
        assert field in row


def test_applications_filter_by_job_and_status(client, auth_headers, make_application):
    application = make_application()
    job_id = application["job_id"]
    params = {"job_id": job_id}

    by_job = client.get("/api/applications", params=params, headers=auth_headers).json()
    assert [item["id"] for item in by_job["items"]] == [application["id"]]

    client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Shortlisted", "version": application["version"]},
        headers=auth_headers,
    )

    shortlisted = client.get("/api/applications", params={**params, "status": "Shortlisted"}, headers=auth_headers)
    rejected = client.get("/api/applications", params={**params, "status": "Rejected"}, headers=auth_headers)
    assert shortlisted.json()["total"] == 1
    assert rejected.json()["total"] == 0


def test_applications_search_matches_candidate_and_job(client, auth_headers, make_job, make_candidate):
    marker = uuid.uuid4().hex[:8]
    candidate = make_candidate(name=f"Person {marker}")
    job = make_job(title=f"Role {marker}")
    application = client.post(
        "/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}, headers=auth_headers
    ).json()

    for term in (f"Person {marker}", f"ROLE {marker}", candidate["email"]):
        found = client.get("/api/applications", params={"search": term}, headers=auth_headers).json()
        assert [item["id"] for item in found["items"]] == [application["id"]]


def test_candidates_search_matches_name_email_and_skill(client, auth_headers, make_candidate):
    marker = uuid.uuid4().hex[:8]
    candidate = make_candidate(name=f"Findable {marker}", skills=[f"skill-{marker}"])

    for term in (f"findable {marker}", candidate["email"], f"skill-{marker}"):
        found = client.get("/api/candidates", params={"search": term}, headers=auth_headers).json()
        assert [item["id"] for item in found] == [candidate["id"]]


def test_search_treats_wildcards_as_plain_text(client, auth_headers):
    found = client.get("/api/candidates", params={"search": "%"}, headers=auth_headers).json()
    assert found == []


def test_search_is_safe_against_sql_injection(client, auth_headers):
    response = client.get("/api/candidates", params={"search": "'; DROP TABLE candidates; --"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []
    assert len(client.get("/api/candidates", headers=auth_headers).json()) >= 250


def test_deleted_records_disappear_from_every_list(client, auth_headers, make_application):
    application = make_application()
    client.delete(f"/api/candidates/{application['candidate_id']}", headers=auth_headers)
    client.delete(f"/api/jobs/{application['job_id']}", headers=auth_headers)

    candidates = client.get("/api/candidates", headers=auth_headers).json()
    jobs = client.get("/api/jobs", headers=auth_headers).json()
    applications = client.get("/api/applications", params={"page_size": 100}, headers=auth_headers).json()

    assert application["candidate_id"] not in {item["id"] for item in candidates}
    assert application["job_id"] not in {item["id"] for item in jobs}
    assert application["id"] not in {item["id"] for item in applications["items"]}


def test_job_detail_counts_applications_by_status(client, auth_headers, make_application):
    application = make_application()
    client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Rejected", "version": application["version"]},
        headers=auth_headers,
    )

    job = client.get(f"/api/jobs/{application['job_id']}", headers=auth_headers).json()

    assert job["application_counts"] == {"Applied": 0, "Shortlisted": 0, "Rejected": 1}


def test_candidate_detail_lists_their_applications(client, auth_headers, make_application):
    application = make_application()

    candidate = client.get(f"/api/candidates/{application['candidate_id']}", headers=auth_headers).json()

    assert [item["id"] for item in candidate["applications"]] == [application["id"]]


def test_health_reports_database_and_model(client):
    body = client.get("/api/health").json()

    assert body["status"] == "ok"
    assert body["database_reachable"] is True
    assert body["model_loaded"] is True
    assert body["model_version"]


def test_metrics_returns_the_saved_evaluation(client, auth_headers):
    body = client.get("/api/model/metrics", headers=auth_headers).json()

    assert set(body["test"]) == {"baseline", "model"}
    assert body["dataset"]["train_applications"] == 400
    assert body["dataset"]["test_applications"] == 100
    assert "f1" in body["test"]["model"]
