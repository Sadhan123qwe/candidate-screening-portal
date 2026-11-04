"""Candidate endpoints. Business logic lives in app/services/candidates.py."""

from fastapi import APIRouter

from app.auth import CurrentUser
from app.db import DbSession
from app.models import Candidate
from app.schemas import CandidateCreate, CandidateDetail, CandidateOut, CandidateUpdate
from app.services import candidates as candidate_service
from app.services.common import get_active
from app.services.presenters import application_counts_by_candidate, to_candidate_detail, to_candidate_out

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("")
def list_candidates(db: DbSession, _user: CurrentUser, search: str | None = None) -> list[CandidateOut]:
    counts = application_counts_by_candidate(db)
    return [
        to_candidate_out(candidate, counts.get(candidate.id, 0))
        for candidate in candidate_service.list_candidates(db, search)
    ]


@router.post("", status_code=201)
def create_candidate(payload: CandidateCreate, db: DbSession, user: CurrentUser) -> CandidateOut:
    return to_candidate_out(candidate_service.create_candidate(db, payload, user))


@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, db: DbSession, _user: CurrentUser) -> CandidateDetail:
    return to_candidate_detail(db, get_active(db, Candidate, candidate_id, "candidate"))


@router.patch("/{candidate_id}")
def update_candidate(candidate_id: int, payload: CandidateUpdate, db: DbSession, user: CurrentUser) -> CandidateOut:
    candidate = candidate_service.update_candidate(db, candidate_id, payload, user)
    return to_candidate_out(candidate, application_counts_by_candidate(db).get(candidate.id, 0))


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: DbSession, user: CurrentUser, version: int | None = None) -> None:
    candidate_service.delete_candidate(db, candidate_id, version, user)
