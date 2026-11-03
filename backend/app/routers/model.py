"""Health check and model information."""

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import CurrentUser
from app.config import get_settings
from app.db import DbSession
from app.errors import AppError
from app.ml import predictor as predictor_module

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


@router.get("/model/metrics")
def model_metrics(_user: CurrentUser) -> dict:
    """Return the evaluation written by scripts/train.py, exactly as it was saved."""
    path = get_settings().metrics_path
    if not path.exists():
        raise AppError(404, "METRICS_UNAVAILABLE", "No metrics found. Run: python -m scripts.train")
    return json.loads(path.read_text(encoding="utf-8"))
