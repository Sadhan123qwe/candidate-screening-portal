"""Simultaneous requests: the database decides, and exactly one request wins."""

import threading
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Application, StatusHistory

ROUNDS = 5


def _send_together(*requests) -> list:
    """Run each callable at the same instant, so they really do overlap."""
    barrier = threading.Barrier(len(requests))

    def run(request):
        barrier.wait()
        return request()

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        return [future.result() for future in [pool.submit(run, request) for request in requests]]


def test_two_identical_application_requests_give_one_201_and_one_409(client, auth_headers, make_job, make_candidate):
    for _ in range(ROUNDS):
        body = {"candidate_id": make_candidate()["id"], "job_id": make_job()["id"]}

        def post():
            return client.post("/api/applications", json=body, headers=auth_headers)

        responses = _send_together(post, post)

        assert Counter(response.status_code for response in responses) == {201: 1, 409: 1}
        with SessionLocal() as db:
            rows = db.scalar(
                select(func.count())
                .select_from(Application)
                .where(Application.candidate_id == body["candidate_id"], Application.job_id == body["job_id"])
            )
        assert rows == 1


def test_two_identical_candidates_give_one_201_and_one_409(client, auth_headers):
    for _ in range(ROUNDS):
        body = {
            "name": "Race",
            "email": f"race-{uuid.uuid4().hex[:10]}@example.com",
            "experience_years": 1,
            "skills": ["python"],
        }

        def post():
            return client.post("/api/candidates", json=body, headers=auth_headers)

        responses = _send_together(post, post)

        assert Counter(response.status_code for response in responses) == {201: 1, 409: 1}


def test_two_simultaneous_status_updates_cannot_both_win(client, auth_headers, make_application):
    for _ in range(ROUNDS):
        application = make_application()

        def patch(new_status):
            return lambda: client.patch(
                f"/api/applications/{application['id']}/status",
                json={"status": new_status, "version": application["version"]},
                headers=auth_headers,
            )

        responses = _send_together(patch("Shortlisted"), patch("Rejected"))

        assert Counter(response.status_code for response in responses) == {200: 1, 409: 1}
        winner = next(response for response in responses if response.status_code == 200).json()
        stored = client.get(f"/api/applications/{application['id']}", headers=auth_headers).json()
        assert stored["status"] == winner["status"]
        assert stored["version"] == application["version"] + 1
        with SessionLocal() as db:
            history = db.scalar(
                select(func.count()).select_from(StatusHistory).where(StatusHistory.application_id == application["id"])
            )
        assert history == 1


def test_two_requests_adding_the_same_new_skill_both_succeed(client, auth_headers):
    for _ in range(ROUNDS):
        new_skill = f"skill-{uuid.uuid4().hex[:10]}"

        def post():
            return client.post(
                "/api/candidates",
                json={
                    "name": "Skill Race",
                    "email": f"skill-race-{uuid.uuid4().hex[:10]}@example.com",
                    "experience_years": 1,
                    "skills": [new_skill],
                },
                headers=auth_headers,
            )

        responses = _send_together(post, post)

        assert [response.status_code for response in responses] == [201, 201]
