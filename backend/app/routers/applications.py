"""Application endpoints. Business logic lives in app/services/applications.py."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.auth import CurrentUser
from app.db import DbSession
from app.models import Application, ApplicationStatus
from app.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationOut,
    ApplicationPage,
    StatusHistoryOut,
    StatusUpdate,
)
from app.services import applications as application_service
from app.services.common import get_active
from app.services.presenters import to_application_detail, to_application_out, to_status_history_out

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("")
def list_applications(
    db: DbSession,
    _user: CurrentUser,
    job_id: int | None = None,
    status: ApplicationStatus | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ApplicationPage:
    items, total = application_service.list_applications(db, job_id, status, search, page, page_size)
    return ApplicationPage(
        items=[to_application_out(application) for application in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", status_code=201)
def create_application(payload: ApplicationCreate, db: DbSession, user: CurrentUser) -> ApplicationOut:
    application = application_service.create_application(db, payload.candidate_id, payload.job_id, user)
    return to_application_out(application)


@router.get("/{application_id}")
def get_application(application_id: int, db: DbSession, _user: CurrentUser) -> ApplicationDetail:
    return to_application_detail(get_active(db, Application, application_id, "application"))


@router.patch("/{application_id}/status")
def update_status(application_id: int, payload: StatusUpdate, db: DbSession, user: CurrentUser) -> ApplicationOut:
    application = application_service.change_status(db, application_id, payload.status, payload.version, user)
    return to_application_out(application)


@router.get("/{application_id}/history")
def get_history(application_id: int, db: DbSession, _user: CurrentUser) -> list[StatusHistoryOut]:
    application = get_active(db, Application, application_id, "application")
    return [to_status_history_out(entry) for entry in application.history]


@router.delete("/{application_id}", status_code=204)
def delete_application(application_id: int, db: DbSession, user: CurrentUser, version: int | None = None) -> None:
    application_service.delete_application(db, application_id, version, user)
