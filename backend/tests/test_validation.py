"""Server-side validation returns 422 with field details, and bad input saves nothing."""

import pytest


def _candidate(**overrides) -> dict:
    return {"name": "Valid Name", "email": "valid@example.com", "experience_years": 1, "skills": ["python"], **overrides}


def _job(**overrides) -> dict:
    return {"title": "Valid Title", "required_skills": ["python"], **overrides}


def _fields(response) -> set[str]:
    return {error["field"] for error in response.json()["errors"]}


@pytest.mark.parametrize(
    "overrides, bad_field",
    [
        ({"email": "not-an-email"}, "email"),
        ({"experience_years": -1}, "experience_years"),
        ({"experience_years": 51}, "experience_years"),
        ({"experience_years": "lots"}, "experience_years"),
        ({"skills": []}, "skills"),
        ({"skills": ["has space"]}, "skills"),
        ({"skills": ["bad!char"]}, "skills"),
        ({"skills": ["   "]}, "skills"),
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "x" * 121}, "name"),
    ],
)
def test_invalid_candidates_return_422_with_the_field(client, auth_headers, overrides, bad_field):
    response = client.post("/api/candidates", json=_candidate(**overrides), headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert bad_field in _fields(response)


@pytest.mark.parametrize(
    "overrides, bad_field",
    [
        ({"title": "  "}, "title"),
        ({"title": "x" * 121}, "title"),
        ({"required_skills": []}, "required_skills"),
        ({"min_experience_years": -0.5}, "min_experience_years"),
        ({"min_experience_years": 51}, "min_experience_years"),
    ],
)
def test_invalid_jobs_return_422_with_the_field(client, auth_headers, overrides, bad_field):
    response = client.post("/api/jobs", json=_job(**overrides), headers=auth_headers)

    assert response.status_code == 422
    assert bad_field in _fields(response)


def test_a_skill_cannot_be_both_required_and_preferred(client, auth_headers):
    response = client.post(
        "/api/jobs", json=_job(required_skills=["python", "sql"], preferred_skills=["SQL "]), headers=auth_headers
    )

    assert response.status_code == 422
    assert "both required and preferred" in response.json()["detail"]


def test_skill_conflict_is_also_caught_across_a_partial_update(client, auth_headers, make_job):
    job = make_job(required_skills=["python"], preferred_skills=["docker"])

    response = client.patch(
        f"/api/jobs/{job['id']}",
        json={"version": job["version"], "required_skills": ["docker"]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "SKILL_CONFLICT"
    assert client.get(f"/api/jobs/{job['id']}", headers=auth_headers).json()["required_skills"] == ["python"]


def test_values_are_normalised(make_candidate):
    candidate = make_candidate(
        name="  Spaced Name  ",
        email="Mixed.Case@Example.COM",
        skills=[" Python ", "SQL", "python", "c++", "c#", "node.js", "scikit-learn"],
    )

    assert candidate["name"] == "Spaced Name"
    assert candidate["email"] == "mixed.case@example.com"
    assert candidate["skills"] == ["c#", "c++", "node.js", "python", "scikit-learn", "sql"]


def test_invalid_status_returns_422(client, auth_headers, make_application):
    application = make_application()

    response = client.patch(
        f"/api/applications/{application['id']}/status",
        json={"status": "Hired", "version": application["version"]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "status" in _fields(response)
    assert client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()["status"] == "Applied"


def test_unknown_fields_are_rejected(client, auth_headers):
    response = client.post("/api/candidates", json=_candidate(role="admin"), headers=auth_headers)
    assert response.status_code == 422


def test_not_found_uses_the_standard_error_shape(client, auth_headers):
    response = client.get("/api/jobs/999999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found.", "code": "JOB_NOT_FOUND"}


def test_applying_with_a_missing_candidate_or_job_returns_404(client, auth_headers, make_job, make_candidate):
    missing_candidate = client.post(
        "/api/applications", json={"candidate_id": 999_999, "job_id": make_job()["id"]}, headers=auth_headers
    )
    missing_job = client.post(
        "/api/applications", json={"candidate_id": make_candidate()["id"], "job_id": 999_999}, headers=auth_headers
    )
    assert missing_candidate.json()["code"] == "CANDIDATE_NOT_FOUND"
    assert missing_job.json()["code"] == "JOB_NOT_FOUND"
