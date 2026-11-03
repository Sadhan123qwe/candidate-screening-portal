"""Shared test setup: a temporary SQLite file per test session, with real migrations."""

import itertools
import os
import shutil
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

# These must be set before anything from `app` is imported, because the engine is
# created at import time. The real storage/app.db is never touched by tests.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="portal-tests-"))
# TEST_DATABASE_URL lets the API tests run against an empty PostgreSQL database instead.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}")
os.environ["JWT_SECRET"] = "test-only-secret-that-is-long-enough-for-hs256"
os.environ["DEMO_USER_EMAIL"] = "recruiter@demo.com"
os.environ["DEMO_USER_PASSWORD"] = "Demo@12345"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ml import predictor as predictor_module  # noqa: E402
from app.ml.predictor import Predictor  # noqa: E402
from app.services.integrity import run_all_checks  # noqa: E402
from scripts.seed import seed_database  # noqa: E402

_unique_numbers = itertools.count(1)


def unique_number() -> int:
    return next(_unique_numbers)


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    # raise_server_exceptions=False returns a 500 like production would, so tests can
    # check the response and the database after an unexpected error.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        with SessionLocal() as db, db.begin():
            seed_database(db)
        yield test_client

        # The suite's writes must leave a clean database, not just pass their asserts.
        report = run_all_checks(engine)
        assert report.ok, f"check_db found problems after the test suite: {report.problems}"
    shutil.rmtree(_TEST_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": "recruiter@demo.com", "password": "Demo@12345"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def make_job(client: TestClient, auth_headers: dict) -> Callable[..., dict]:
    def _make_job(**overrides) -> dict:
        body = {
            "title": f"Test job {unique_number()}",
            "description": "A job created by a test.",
            "min_experience_years": 1,
            "required_skills": ["python", "sql"],
            "preferred_skills": ["docker"],
            **overrides,
        }
        response = client.post("/api/jobs", json=body, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_job


@pytest.fixture
def make_candidate(client: TestClient, auth_headers: dict) -> Callable[..., dict]:
    def _make_candidate(**overrides) -> dict:
        number = unique_number()
        body = {
            "name": f"Test candidate {number}",
            "email": f"test-candidate-{number}@example.com",
            "experience_years": 2,
            "skills": ["python", "sql"],
            **overrides,
        }
        response = client.post("/api/candidates", json=body, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_candidate


@pytest.fixture
def make_application(client: TestClient, auth_headers: dict, make_job, make_candidate) -> Callable[..., dict]:
    def _make_application() -> dict:
        body = {"candidate_id": make_candidate()["id"], "job_id": make_job()["id"]}
        response = client.post("/api/applications", json=body, headers=auth_headers)
        assert response.status_code == 201, response.text
        return response.json()

    return _make_application


@pytest.fixture
def model_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Behave as if model.joblib doesn't exist, for the length of one test."""
    monkeypatch.setattr(predictor_module, "_predictor", Predictor(None))
