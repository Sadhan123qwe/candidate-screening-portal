"""The error analysis, and the rule that documents can only show numbers from the artifacts."""

import json

from app.config import get_settings
from scripts.build_report import README_PATH, REPORT_PATH, build_readme, build_report

FORBIDDEN_KEYS = {"name", "email", "candidate_id", "candidate_name", "candidate_email"}


def _metrics() -> dict:
    return json.loads(get_settings().metrics_path.read_text(encoding="utf-8"))


def _read(path) -> str:
    # A Windows checkout may use CRLF, which isn't a real difference.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_errors_endpoint_needs_a_login(client):
    assert client.get("/api/model/errors").status_code == 401


def test_errors_endpoint_lists_every_test_set_mistake(client, auth_headers):
    response = client.get("/api/model/errors", headers=auth_headers)

    assert response.status_code == 200
    errors = response.json()["errors"]
    matrix = _metrics()["test"]["model"]["confusion_matrix"]
    kinds = [error["error_type"] for error in errors]
    assert kinds.count("false_positive") == matrix["fp"]
    assert kinds.count("false_negative") == matrix["fn"]


def test_each_error_has_what_the_analysis_needs(client, auth_headers):
    errors = client.get("/api/model/errors", headers=auth_headers).json()["errors"]
    threshold = _metrics()["decision_threshold"]

    for error in errors:
        assert error["application_id"].startswith("A")
        assert error["job_title"]
        assert 0 <= error["required_overlap_ratio"] <= 1
        assert isinstance(error["missing_required_skills"], list)
        assert error["experience_years"] >= 0
        assert error["minimum_experience_years"] >= 0
        # A false alarm scored at or above the threshold with label 0, and a miss the reverse.
        if error["error_type"] == "false_positive":
            assert error["predicted_probability"] >= threshold and error["true_label"] == 0
        else:
            assert error["predicted_probability"] < threshold and error["true_label"] == 1


def test_errors_never_identify_a_candidate(client, auth_headers):
    response = client.get("/api/model/errors", headers=auth_headers)

    for error in response.json()["errors"]:
        assert not set(error) & FORBIDDEN_KEYS
    assert "@" not in response.text


def test_errors_endpoint_explains_a_missing_file(client, auth_headers, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "error_analysis_path", tmp_path / "missing.json")

    response = client.get("/api/model/errors", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["code"] == "ERROR_ANALYSIS_UNAVAILABLE"


def test_model_report_matches_the_artifacts():
    assert _read(REPORT_PATH) == build_report(), "Run: python -m scripts.build_report"


def test_readme_results_match_the_artifacts():
    current = _read(README_PATH)
    assert current == build_readme(current), "Run: python -m scripts.build_report"
