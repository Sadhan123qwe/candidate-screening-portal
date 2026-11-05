"""Sorting, CSV export and the jobs summary. All read-only."""

import csv
import io

from app.ml import predictor as predictor_module
from app.ml.predictor import Predictor

CSV_HEADER = ["Candidate name", "Email", "Job", "Status", "Prediction", "Probability", "Created date"]


def _apply(client, auth_headers, candidate, job):
    response = client.post(
        "/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _job_with_three_applications(client, auth_headers, make_job, make_candidate):
    """Three candidates with clearly different skill coverage, so their scores differ."""
    job = make_job(required_skills=["python", "sql", "docker"], preferred_skills=[])
    for skills in (["python", "sql", "docker"], ["python"], ["rust"]):
        _apply(client, auth_headers, make_candidate(skills=skills), job)
    return job


def _read_csv(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def _probabilities(items) -> list[float]:
    return [item["prediction"]["probability"] for item in items]


def test_sort_by_probability_high_to_low_and_low_to_high(client, auth_headers, make_job, make_candidate):
    job = _job_with_three_applications(client, auth_headers, make_job, make_candidate)

    high = client.get("/api/applications", params={"job_id": job["id"], "sort": "probability_desc"}, headers=auth_headers).json()
    low = client.get("/api/applications", params={"job_id": job["id"], "sort": "probability_asc"}, headers=auth_headers).json()

    assert _probabilities(high["items"]) == sorted(_probabilities(high["items"]), reverse=True)
    assert _probabilities(low["items"]) == sorted(_probabilities(low["items"]))
    assert len(set(_probabilities(high["items"]))) > 1


def test_sort_by_date_both_ways(client, auth_headers, make_job, make_candidate):
    job = _job_with_three_applications(client, auth_headers, make_job, make_candidate)

    newest = client.get("/api/applications", params={"job_id": job["id"], "sort": "date_desc"}, headers=auth_headers).json()["items"]
    oldest = client.get("/api/applications", params={"job_id": job["id"], "sort": "date_asc"}, headers=auth_headers).json()["items"]

    assert [item["id"] for item in newest] == [item["id"] for item in reversed(oldest)]
    assert newest[0]["created_at"] >= newest[-1]["created_at"]


def test_default_order_is_unchanged_newest_first(client, auth_headers, make_job, make_candidate):
    job = _job_with_three_applications(client, auth_headers, make_job, make_candidate)
    params = {"job_id": job["id"]}

    default = client.get("/api/applications", params=params, headers=auth_headers).json()["items"]
    newest = client.get("/api/applications", params={**params, "sort": "date_desc"}, headers=auth_headers).json()["items"]

    assert [item["id"] for item in default] == [item["id"] for item in newest]


def test_sorting_doesnt_change_totals_and_pages_dont_overlap(client, auth_headers):
    params = {"sort": "probability_desc", "page_size": 20}
    first = client.get("/api/applications", params={**params, "page": 1}, headers=auth_headers).json()
    second = client.get("/api/applications", params={**params, "page": 2}, headers=auth_headers).json()
    unsorted_total = client.get("/api/applications", headers=auth_headers).json()["total"]

    assert first["total"] == unsorted_total
    assert not {item["id"] for item in first["items"]} & {item["id"] for item in second["items"]}
    assert _probabilities(first["items"])[-1] >= _probabilities(second["items"])[0]


def test_unknown_sort_is_refused(client, auth_headers):
    assert client.get("/api/applications", params={"sort": "name"}, headers=auth_headers).status_code == 422


def test_export_needs_a_login(client):
    assert client.get("/api/applications/export").status_code == 401


def test_export_is_a_csv_download_with_the_expected_columns(client, auth_headers, make_job, make_candidate):
    job = make_job()
    candidate = make_candidate(name="Export Person")
    _apply(client, auth_headers, candidate, job)

    response = client.get("/api/applications/export", params={"job_id": job["id"]}, headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="applications.csv"' in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    header, row = _read_csv(response)
    assert header == CSV_HEADER
    assert row[:4] == ["Export Person", candidate["email"], job["title"], "Applied"]
    assert row[4] in ("Potential Match", "Needs Review")
    assert 0 <= float(row[5]) <= 1
    assert len(row[6]) == len("2026-01-01")


def test_export_respects_every_filter_and_ignores_pagination(client, auth_headers, make_job, make_candidate):
    job = _job_with_three_applications(client, auth_headers, make_job, make_candidate)
    base = {"job_id": job["id"]}

    everything = _read_csv(client.get("/api/applications/export", params=base, headers=auth_headers))
    rejected = _read_csv(client.get("/api/applications/export", params={**base, "status": "Rejected"}, headers=auth_headers))
    label = everything[1][4]
    by_label = _read_csv(client.get("/api/applications/export", params={**base, "prediction": label}, headers=auth_headers))
    searched = _read_csv(client.get("/api/applications/export", params={**base, "search": everything[1][1]}, headers=auth_headers))

    assert len(everything) == 4
    assert rejected == [CSV_HEADER]
    assert all(row[4] == label for row in by_label[1:]) and len(by_label) >= 2
    assert searched[1:] == [everything[1]]

    whole_list = _read_csv(client.get("/api/applications/export", headers=auth_headers))
    assert len(whole_list) - 1 == client.get("/api/applications", headers=auth_headers).json()["total"] > 100


def test_export_follows_the_requested_sort(client, auth_headers, make_job, make_candidate):
    job = _job_with_three_applications(client, auth_headers, make_job, make_candidate)

    rows = _read_csv(
        client.get("/api/applications/export", params={"job_id": job["id"], "sort": "probability_asc"}, headers=auth_headers)
    )[1:]

    probabilities = [float(row[5]) for row in rows]
    assert probabilities == sorted(probabilities)


def test_export_leaves_out_soft_deleted_applications(client, auth_headers, make_application):
    application = make_application()
    client.delete(f"/api/applications/{application['id']}", headers=auth_headers)

    rows = _read_csv(client.get("/api/applications/export", params={"job_id": application["job_id"]}, headers=auth_headers))

    assert rows == [CSV_HEADER]


def test_export_stops_names_running_as_spreadsheet_formulas(client, auth_headers, make_job, make_candidate):
    job = make_job(title="=HYPERLINK(1)")
    _apply(client, auth_headers, make_candidate(name="=cmd|calc"), job)

    row = _read_csv(client.get("/api/applications/export", params={"job_id": job["id"]}, headers=auth_headers))[1]

    assert row[0] == "'=cmd|calc"
    assert row[2] == "'=HYPERLINK(1)"


def test_export_shows_unavailable_predictions_plainly(client, auth_headers, make_application, monkeypatch):
    # Created first, so the row has its prediction: the suite's final check requires one.
    application = make_application()
    monkeypatch.setattr(predictor_module, "_predictor", Predictor(None))

    row = _read_csv(client.get("/api/applications/export", params={"job_id": application["job_id"]}, headers=auth_headers))[1]

    assert row[4:6] == ["Unavailable", ""]


def test_export_doesnt_shadow_a_real_application(client, auth_headers, make_application):
    application = make_application()
    assert client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()["id"] == application["id"]


def test_jobs_summary_needs_a_login(client):
    assert client.get("/api/jobs/summary").status_code == 401


def _summary_for(client, auth_headers, job_id) -> dict:
    rows = client.get("/api/jobs/summary", headers=auth_headers).json()
    return next(row for row in rows if row["job_id"] == job_id)


def test_jobs_summary_counts_statuses_and_potential_matches(client, auth_headers, make_job, make_candidate):
    job = _job_with_three_applications(client, auth_headers, make_job, make_candidate)
    items = client.get("/api/applications", params={"job_id": job["id"]}, headers=auth_headers).json()["items"]
    client.patch(f"/api/applications/{items[0]['id']}/status", json={"status": "Shortlisted", "version": items[0]["version"]}, headers=auth_headers)
    client.patch(f"/api/applications/{items[1]['id']}/status", json={"status": "Rejected", "version": items[1]["version"]}, headers=auth_headers)
    expected_matches = sum(item["prediction"]["label"] == "Potential Match" for item in items)

    summary = _summary_for(client, auth_headers, job["id"])

    assert summary == {"job_id": job["id"], "applied": 1, "shortlisted": 1, "rejected": 1, "potential_match": expected_matches}


def test_jobs_summary_includes_a_job_with_no_applications(client, auth_headers, make_job):
    job = make_job()
    assert _summary_for(client, auth_headers, job["id"]) == {
        "job_id": job["id"],
        "applied": 0,
        "shortlisted": 0,
        "rejected": 0,
        "potential_match": 0,
    }


def test_jobs_summary_leaves_out_deleted_jobs_and_applications(client, auth_headers, make_application, make_job):
    application = make_application()
    client.delete(f"/api/applications/{application['id']}", headers=auth_headers)
    assert _summary_for(client, auth_headers, application["job_id"])["applied"] == 0
    assert _summary_for(client, auth_headers, application["job_id"])["potential_match"] == 0

    job = make_job()
    client.delete(f"/api/jobs/{job['id']}", headers=auth_headers)
    rows = client.get("/api/jobs/summary", headers=auth_headers).json()
    assert job["id"] not in {row["job_id"] for row in rows}


def test_jobs_summary_totals_match_the_applications_list(client, auth_headers):
    rows = client.get("/api/jobs/summary", headers=auth_headers).json()
    matches = client.get("/api/applications/summary", params={"prediction": "Potential Match"}, headers=auth_headers).json()
    everything = client.get("/api/applications/summary", headers=auth_headers).json()

    assert sum(row["potential_match"] for row in rows) == matches["total"]
    assert sum(row["applied"] + row["shortlisted"] + row["rejected"] for row in rows) == everything["total"]


def test_jobs_summary_doesnt_invent_predictions_without_a_model(client, auth_headers, make_job, monkeypatch):
    job = make_job()
    monkeypatch.setattr(predictor_module, "_predictor", Predictor(None))

    assert _summary_for(client, auth_headers, job["id"])["potential_match"] is None


def test_jobs_summary_doesnt_shadow_a_real_job(client, auth_headers, make_job):
    job = make_job()
    assert client.get(f"/api/jobs/{job['id']}", headers=auth_headers).json()["id"] == job["id"]
