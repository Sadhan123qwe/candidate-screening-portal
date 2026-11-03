"""Login, tokens and protected routes."""

from datetime import timedelta

import jwt
import pytest

from app.config import get_settings
from app.models import utcnow

PROTECTED_ROUTES = [
    ("GET", "/api/auth/me"),
    ("GET", "/api/jobs"),
    ("POST", "/api/jobs"),
    ("GET", "/api/jobs/1"),
    ("PATCH", "/api/jobs/1"),
    ("DELETE", "/api/jobs/1"),
    ("GET", "/api/candidates"),
    ("POST", "/api/candidates"),
    ("GET", "/api/candidates/1"),
    ("PATCH", "/api/candidates/1"),
    ("DELETE", "/api/candidates/1"),
    ("GET", "/api/applications"),
    ("POST", "/api/applications"),
    ("GET", "/api/applications/1"),
    ("PATCH", "/api/applications/1/status"),
    ("DELETE", "/api/applications/1"),
    ("GET", "/api/applications/1/history"),
    ("GET", "/api/model/metrics"),
]


def _token(**claims) -> str:
    settings = get_settings()
    payload = {"sub": "1", "exp": utcnow() + timedelta(minutes=5), **claims}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_login_succeeds_with_demo_credentials(client):
    response = client.post("/api/auth/login", json={"email": "recruiter@demo.com", "password": "Demo@12345"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "recruiter@demo.com"
    assert "password_hash" not in body["user"]


def test_login_email_is_not_case_sensitive(client):
    response = client.post("/api/auth/login", json={"email": "RECRUITER@demo.com", "password": "Demo@12345"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "email, password",
    [("recruiter@demo.com", "wrong-password"), ("nobody@demo.com", "Demo@12345")],
)
def test_login_fails_with_the_same_message_for_any_bad_credentials(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    # The same message either way, so the API can't be used to discover valid emails.
    assert response.json() == {"detail": "Incorrect email or password.", "code": "INVALID_CREDENTIALS"}


def test_passwords_longer_than_bcrypts_limit_do_not_crash_login(client):
    response = client.post("/api/auth/login", json={"email": "recruiter@demo.com", "password": "x" * 200})
    assert response.status_code == 401


@pytest.mark.parametrize("method, path", PROTECTED_ROUTES)
def test_protected_routes_return_401_without_a_token(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_health_needs_no_token(client):
    assert client.get("/api/health").status_code == 200


def test_me_returns_the_logged_in_user(client, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "recruiter@demo.com"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-real-token",
        _token(exp=utcnow() - timedelta(minutes=1)),  # expired
        _token(sub="999999"),  # user doesn't exist
        _token(sub="not-a-number"),
        jwt.encode({"sub": "1", "exp": utcnow() + timedelta(minutes=5)}, "a-different-secret-" * 3, algorithm="HS256"),
    ],
    ids=["garbage", "expired", "unknown-user", "bad-subject", "wrong-signature"],
)
def test_invalid_tokens_are_rejected(client, token):
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
