"""Job endpoints. Business logic lives in app/services/jobs.py."""

from fastapi import APIRouter

from app.auth import CurrentUser
from app.db import DbSession
from app.models import Job
from app.schemas import JobCreate, JobOut, JobUpdate
from app.services import jobs as job_service
from app.services.common import get_active
from app.services.presenters import application_counts_by_job, to_job_out

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", status_code=201)
def create_job(payload: JobCreate, db: DbSession, user: CurrentUser) -> JobOut:
    return to_job_out(job_service.create_job(db, payload, user))


@router.get("/{job_id}")
def get_job(job_id: int, db: DbSession, _user: CurrentUser) -> JobOut:
    job = get_active(db, Job, job_id, "job")
    return to_job_out(job, application_counts_by_job(db).get(job.id))


@router.patch("/{job_id}")
def update_job(job_id: int, payload: JobUpdate, db: DbSession, user: CurrentUser) -> JobOut:
    job = job_service.update_job(db, job_id, payload, user)
    return to_job_out(job, application_counts_by_job(db).get(job.id))


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: DbSession, user: CurrentUser, version: int | None = None) -> None:
    job_service.delete_job(db, job_id, version, user)
