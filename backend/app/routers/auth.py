"""Login and the current user."""

from fastapi import APIRouter
from sqlalchemy import select

from app.auth import CurrentUser, create_access_token, hash_password, verify_password
from app.db import DbSession
from app.errors import AppError
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Checked when the email is unknown, so that case takes as long as a wrong password
# and response time can't reveal which emails have accounts.
_TIMING_DECOY_HASH = hash_password("timing-decoy")


def _to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


@router.post("/login")
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    password_hash = user.password_hash if user else _TIMING_DECOY_HASH
    if not verify_password(payload.password, password_hash) or user is None:
        raise AppError(401, "INVALID_CREDENTIALS", "Incorrect email or password.")
    return LoginResponse(access_token=create_access_token(user), user=_to_user_out(user))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return _to_user_out(user)
