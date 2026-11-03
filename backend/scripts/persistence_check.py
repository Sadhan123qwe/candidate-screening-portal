"""Prove that data survives a crash. Run from backend/: python -m scripts.persistence_check

Starts the real server on a temporary database, writes through the API, kills the
process with no chance to clean up, restarts it and compares every record. Your real
database is never touched.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent
STARTUP_TIMEOUT_SECONDS = 60


class CheckFailed(Exception):
    pass


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _run_step(args: list[str], env: dict[str, str]) -> None:
    result = subprocess.run([sys.executable, "-m", *args], cwd=BACKEND_DIR, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise CheckFailed(f"'{' '.join(args)}' failed:\n{result.stdout}\n{result.stderr}")


def _start_server(env: dict[str, str], port: int) -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=BACKEND_DIR,
        env=env,
    )
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise CheckFailed(f"The server exited during startup with code {process.returncode}")
        try:
            if httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=2).status_code == 200:
                return process
        except httpx.TransportError:
            pass
        time.sleep(0.25)
    process.kill()
    raise CheckFailed("The server did not become healthy in time")


def _crash(process: subprocess.Popen) -> None:
    # kill() gives the process no chance to flush or shut down, like a power cut.
    process.kill()
    process.wait()


def _expect(response: httpx.Response, status_code: int) -> dict | list:
    if response.status_code != status_code:
        raise CheckFailed(
            f"{response.request.method} {response.request.url}: expected {status_code}, "
            f"got {response.status_code}: {response.text}"
        )
    return response.json()


def _login(client: httpx.Client) -> None:
    body = _expect(
        client.post("/api/auth/login", json={"email": "recruiter@demo.com", "password": "Demo@12345"}), 200
    )
    client.headers["Authorization"] = f"Bearer {body['access_token']}"


def _write_records(client: httpx.Client) -> dict[str, int]:
    unique = uuid.uuid4().hex[:8]
    job = _expect(
        client.post(
            "/api/jobs",
            json={"title": f"Persistence job {unique}", "required_skills": ["python"], "preferred_skills": ["sql"]},
        ),
        201,
    )
    candidate = _expect(
        client.post(
            "/api/candidates",
            json={
                "name": f"Persistence candidate {unique}",
                "email": f"persist-{unique}@example.com",
                "experience_years": 2,
                "skills": ["python"],
            },
        ),
        201,
    )
    application = _expect(
        client.post("/api/applications", json={"candidate_id": candidate["id"], "job_id": job["id"]}), 201
    )
    _expect(
        client.patch(
            f"/api/applications/{application['id']}/status",
            json={"status": "Shortlisted", "version": application["version"]},
        ),
        200,
    )
    return {"job": job["id"], "candidate": candidate["id"], "application": application["id"]}


def _read_records(client: httpx.Client, ids: dict[str, int]) -> dict:
    return {
        "job": _expect(client.get(f"/api/jobs/{ids['job']}"), 200),
        "candidate": _expect(client.get(f"/api/candidates/{ids['candidate']}"), 200),
        "application": _expect(client.get(f"/api/applications/{ids['application']}"), 200),
        "history": _expect(client.get(f"/api/applications/{ids['application']}/history"), 200),
    }


def _verify(before: dict, after: dict) -> None:
    for name in before:
        if before[name] != after[name]:
            raise CheckFailed(f"{name} changed across the restart:\n  before: {before[name]}\n  after:  {after[name]}")
    if after["application"]["status"] != "Shortlisted":
        raise CheckFailed(f"Status was lost: {after['application']['status']}")
    if len(after["history"]) != 1 or after["history"][0]["new_status"] != "Shortlisted":
        raise CheckFailed(f"Status history was lost: {after['history']}")


def run_check(workdir: Path) -> None:
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{(workdir / 'check.db').as_posix()}",
        "DEMO_USER_EMAIL": "recruiter@demo.com",
        "DEMO_USER_PASSWORD": "Demo@12345",
    }
    print("Preparing a temporary database...")
    _run_step(["alembic", "upgrade", "head"], env)
    _run_step(["scripts.seed"], env)

    port = _free_port()
    process = _start_server(env, port)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            _login(client)
            ids = _write_records(client)
            before = _read_records(client, ids)
        print("Wrote a job, a candidate, an application and a status change.")
    finally:
        _crash(process)
    print("Killed the server process.")

    process = _start_server(env, port)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            _login(client)
            after = _read_records(client, ids)
        _verify(before, after)
        print("Restarted: every record, the status and the history are unchanged.")
    finally:
        _crash(process)

    _run_step(["scripts.check_db"], env)
    print("check_db reports no problems on the restarted database.")


def main() -> int:
    # ignore_cleanup_errors: Windows can briefly hold a killed process's files open.
    with tempfile.TemporaryDirectory(prefix="persistence-check-", ignore_cleanup_errors=True) as workdir:
        try:
            run_check(Path(workdir))
        except CheckFailed as error:
            print(f"FAIL: {error}")
            return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
