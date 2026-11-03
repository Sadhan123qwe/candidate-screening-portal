"""Password hashing, JWT creation and the get_current_user dependency."""

from datetime import timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.db import DbSession
from app.errors import AppError
from app.models import User, utcnow

# auto_error=False lets us return the standard error shape instead of FastAPI's default.
bearer_scheme = HTTPBearer(auto_error=False)

# bcrypt only reads the first 72 bytes, and newer versions raise an error on longer input.
BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))


def create_access_token(user: User) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user.id),
        "exp": utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _unauthorized(detail: str) -> AppError:
    return AppError(401, "UNAUTHORIZED", detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise _unauthorized("Authentication required.")

    settings = get_settings()
    try:
        # Passing algorithms explicitly blocks tokens signed with a different algorithm.
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired token.") from None

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Invalid or expired token.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
