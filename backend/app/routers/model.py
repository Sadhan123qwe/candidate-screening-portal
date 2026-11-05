"""Health check and model information."""

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import CurrentUser
from app.config import get_settings
from app.db import DbSession
from app.errors import AppError
from app.ml import predictor as predictor_module
from app.models import Application, Candidate, Job
from app.schemas import PortalStats

router = APIRouter(prefix="/api", tags=["model"])


@router.get("/health")
def health(db: DbSession) -> JSONResponse:
    """Public, so a load balancer or a script can use it without logging in."""
    try:
        db.execute(select(1))
        database_ok = True
    except SQLAlchemyError:
        db.rollback()
        database_ok = False

    predictor = predictor_module.get_predictor()
    return JSONResponse(
        {
            "status": "ok" if database_ok else "unavailable",
            "database_reachable": database_ok,
            "model_loaded": predictor.available,
            "model_version": predictor.model_version,
        },
        status_code=200 if database_ok else 503,
    )


@router.get("/stats")
def portal_stats(db: DbSession) -> PortalStats:
    """Public, because the login page shows these totals. It exposes nothing but counts."""

    def active_count(model: type[Job] | type[Candidate] | type[Application]) -> int:
        return db.scalar(select(func.count()).select_from(model).where(model.deleted_at.is_(None)))

    return PortalStats(jobs=active_count(Job), candidates=active_count(Candidate), applications=active_count(Application))


@router.get("/model/errors")
def model_errors(_user: CurrentUser) -> dict:
    """Every test-set mistake, as written by scripts/train.py. It holds no names or emails."""
    path = get_settings().error_analysis_path
    if not path.exists():
        raise AppError(404, "ERROR_ANALYSIS_UNAVAILABLE", "No error analysis found. Run: python -m scripts.train")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/model/metrics")
def model_metrics(_user: CurrentUser) -> dict:
    """Return the evaluation written by scripts/train.py, exactly as it was saved."""
    path = get_settings().metrics_path
    if not path.exists():
        raise AppError(404, "METRICS_UNAVAILABLE", "No metrics found. Run: python -m scripts.train")
    return json.loads(path.read_text(encoding="utf-8"))
