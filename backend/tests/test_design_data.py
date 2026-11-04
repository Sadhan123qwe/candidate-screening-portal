"""Read-only data added for the redesigned screens. None of it changes existing behaviour."""

from app.ml.features import FEATURE_NAMES


def _set_status(client, auth_headers, application, status):
    response = client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": status, "version": application["version"]},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text


def _apply(client, auth_headers, candidate, job):
    response = client.post(
        "/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_summary_counts_each_status_for_one_job(client, auth_headers, make_job, make_candidate):
    job = make_job()
    _apply(client, auth_headers, make_candidate(), job)
    shortlisted = _apply(client, auth_headers, make_candidate(), job)
    rejected = _apply(client, auth_headers, make_candidate(), job)
    _set_status(client, auth_headers, shortlisted, "Shortlisted")
    _set_status(client, auth_headers, rejected, "Rejected")

    response = client.get("/api/applications/summary", params={"job_id": job["id"]}, headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"total": 3, "applied": 1, "shortlisted": 1, "rejected": 1}


def test_summary_without_a_job_covers_every_job(client, auth_headers, make_application):
    application = make_application()
    everything = client.get("/api/applications/summary", headers=auth_headers).json()
    one_job = client.get("/api/applications/summary", params={"job_id": application["job_id"]}, headers=auth_headers).json()

    assert everything["total"] == everything["applied"] + everything["shortlisted"] + everything["rejected"]
    assert everything["total"] > one_job["total"] == 1


def test_summary_agrees_with_the_list_for_search(client, auth_headers, make_job, make_candidate):
    job = make_job()
    _apply(client, auth_headers, make_candidate(name="Summary Search Target"), job)
    _apply(client, auth_headers, make_candidate(), job)
    params = {"job_id": job["id"], "search": "Summary Search Target"}

    summary = client.get("/api/applications/summary", params=params, headers=auth_headers).json()
    listing = client.get("/api/applications", params=params, headers=auth_headers).json()

    assert summary["total"] == listing["total"] == 1


def test_summary_leaves_out_soft_deleted_applications(client, auth_headers, make_application):
    application = make_application()
    client.delete(f"/api/applications/{application['id']}", headers=auth_headers)

    summary = client.get("/api/applications/summary", params={"job_id": application["job_id"]}, headers=auth_headers)

    assert summary.json() == {"total": 0, "applied": 0, "shortlisted": 0, "rejected": 0}


def test_summary_needs_a_login(client):
    assert client.get("/api/applications/summary").status_code == 401


def test_summary_route_does_not_shadow_a_real_application_id(client, auth_headers, make_application):
    application = make_application()
    response = client.get(f"/api/applications/{application['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == application["id"]


def test_prediction_filter_returns_only_that_label(client, auth_headers):
    for label in ("Potential Match", "Needs Review"):
        body = client.get("/api/applications", params={"prediction": label, "page_size": 100}, headers=auth_headers).json()
        assert body["total"] > 0
        assert {item["prediction"]["label"] for item in body["items"]} == {label}


def test_prediction_filter_totals_add_up_and_match_the_summary(client, auth_headers):
    match = client.get("/api/applications/summary", params={"prediction": "Potential Match"}, headers=auth_headers).json()
    review = client.get("/api/applications/summary", params={"prediction": "Needs Review"}, headers=auth_headers).json()
    everything = client.get("/api/applications/summary", headers=auth_headers).json()
    listed = client.get("/api/applications", params={"prediction": "Potential Match"}, headers=auth_headers).json()

    assert match["total"] + review["total"] == everything["total"]
    assert listed["total"] == match["total"]


def test_unknown_prediction_filter_is_refused(client, auth_headers):
    assert client.get("/api/applications", params={"prediction": "Maybe"}, headers=auth_headers).status_code == 422


def test_list_is_unchanged_when_the_prediction_filter_is_left_out(client, auth_headers):
    unfiltered = client.get("/api/applications", headers=auth_headers).json()
    summary = client.get("/api/applications/summary", headers=auth_headers).json()
    assert unfiltered["total"] == summary["total"]


def test_rows_include_required_skill_match_and_experience(client, auth_headers, make_job, make_candidate):
    job = make_job(required_skills=["python", "sql", "go"], preferred_skills=[])
    candidate = make_candidate(skills=["python", "go", "rust"], experience_years=1.5)
    _apply(client, auth_headers, candidate, job)

    row = client.get("/api/applications", params={"job_id": job["id"]}, headers=auth_headers).json()["items"][0]

    assert row["required_matched"] == 2
    assert row["required_total"] == 3
    assert row["candidate_experience_years"] == 1.5
    assert row["candidate_email"] == candidate["email"]


def test_detail_splits_skills_and_explains_the_experience_gap(client, auth_headers, make_job, make_candidate):
    job = make_job(required_skills=["python", "sql"], preferred_skills=["docker", "git"], min_experience_years=2)
    candidate = make_candidate(skills=["python", "git", "rust"], experience_years=0.5, profile_summary="Built things.")
    application = _apply(client, auth_headers, candidate, job)

    detail = client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()

    assert detail["required_skills_matched"] == ["python"]
    assert detail["required_skills_missing"] == ["sql"]
    assert detail["preferred_skills_matched"] == ["git"]
    assert detail["preferred_skills_missing"] == ["docker"]
    assert detail["other_candidate_skills"] == ["rust"]
    assert detail["job_min_experience_years"] == 2
    assert detail["experience_gap"] == -1.5
    assert detail["candidate_profile_summary"] == "Built things."
    assert detail["candidate_email"] == candidate["email"]
    assert detail["imported_from_dataset"] is False
    assert len(detail["top_features"]) == 3
    assert all(item["feature"] in FEATURE_NAMES for item in detail["top_features"])


def test_seeded_applications_are_marked_as_imported(client, auth_headers):
    listing = client.get("/api/applications", params={"search": "Synthetic Candidate 001"}, headers=auth_headers).json()
    detail = client.get(f"/api/applications/{listing['items'][0]['id']}", headers=auth_headers).json()
    assert detail["imported_from_dataset"] is True


def test_candidate_lists_count_active_applications(client, auth_headers, make_job, make_candidate):
    candidate = make_candidate(name="Counted Candidate")
    assert candidate["application_count"] == 0
    _apply(client, auth_headers, candidate, make_job())
    deleted = _apply(client, auth_headers, candidate, make_job())
    client.delete(f"/api/applications/{deleted['id']}", headers=auth_headers)

    row = client.get("/api/candidates", params={"search": candidate["email"]}, headers=auth_headers).json()[0]
    detail = client.get(f"/api/candidates/{candidate['id']}", headers=auth_headers).json()
    updated = client.patch(
        f"/api/candidates/{candidate['id']}",
        json={"version": candidate["version"], "name": "Counted Candidate Renamed"},
        headers=auth_headers,
    ).json()

    assert row["application_count"] == 1
    assert detail["application_count"] == 1
    assert updated["application_count"] == 1


def test_stats_are_public_and_count_only_active_rows(client, auth_headers, make_job, make_candidate):
    before = client.get("/api/stats")
    assert before.status_code == 200
    application = _apply(client, auth_headers, make_candidate(), make_job())

    added = client.get("/api/stats").json()
    assert added["jobs"] == before.json()["jobs"] + 1
    assert added["candidates"] == before.json()["candidates"] + 1
    assert added["applications"] == before.json()["applications"] + 1
    assert set(added) == {"jobs", "candidates", "applications"}

    client.delete(f"/api/applications/{application['id']}", headers=auth_headers)
    assert client.get("/api/stats").json()["applications"] == before.json()["applications"]
