"""An update based on an old copy of a row gets a 409 and changes nothing."""


def test_stale_status_update_is_refused_and_data_is_unchanged(client, auth_headers, make_application):
    application = make_application()
    url = f"/api/applications/{application['id']}/status"

    first = client.patch(url, json={"status": "Shortlisted", "version": application["version"]}, headers=auth_headers)
    assert first.status_code == 200
    assert first.json()["version"] == application["version"] + 1

    # A second recruiter still has the original version on screen.
    stale = client.patch(url, json={"status": "Rejected", "version": application["version"]}, headers=auth_headers)

    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_UPDATE"
    stored = client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()
    assert stored["status"] == "Shortlisted"
    assert stored["version"] == first.json()["version"]


def test_stale_candidate_update_is_refused(client, auth_headers, make_candidate):
    candidate = make_candidate()
    url = f"/api/candidates/{candidate['id']}"

    client.patch(url, json={"version": candidate["version"], "name": "First Edit"}, headers=auth_headers)
    stale = client.patch(url, json={"version": candidate["version"], "name": "Second Edit"}, headers=auth_headers)

    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_UPDATE"
    assert client.get(url, headers=auth_headers).json()["name"] == "First Edit"


def test_stale_job_update_is_refused(client, auth_headers, make_job):
    job = make_job()
    url = f"/api/jobs/{job['id']}"

    client.patch(url, json={"version": job["version"], "title": "First Edit"}, headers=auth_headers)
    stale = client.patch(url, json={"version": job["version"], "title": "Second Edit"}, headers=auth_headers)

    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_UPDATE"
    assert client.get(url, headers=auth_headers).json()["title"] == "First Edit"


def test_changing_only_skills_still_bumps_the_version(client, auth_headers, make_candidate):
    """Skills live in another table, so a naive version column would miss this edit."""
    candidate = make_candidate(skills=["python"])
    url = f"/api/candidates/{candidate['id']}"

    response = client.patch(url, json={"version": candidate["version"], "skills": ["python", "sql"]}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["version"] == candidate["version"] + 1
    assert response.json()["skills"] == ["python", "sql"]


def test_stale_delete_is_refused_when_a_version_is_sent(client, auth_headers, make_candidate):
    candidate = make_candidate()
    url = f"/api/candidates/{candidate['id']}"
    client.patch(url, json={"version": candidate["version"], "name": "Edited"}, headers=auth_headers)

    response = client.delete(url, params={"version": candidate["version"]}, headers=auth_headers)

    assert response.status_code == 409
    assert client.get(url, headers=auth_headers).status_code == 200


def test_update_requires_a_version(client, auth_headers, make_application):
    application = make_application()
    response = client.patch(
        f"/api/applications/{application['id']}/status", json={"status": "Shortlisted"}, headers=auth_headers
    )
    assert response.status_code == 422
