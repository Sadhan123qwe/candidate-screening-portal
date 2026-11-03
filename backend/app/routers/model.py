"""Health check and model information."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import DbSession
from app.ml import predictor as predictor_module

router = APIRouter(prefix="/api", tags=["model"])


@router.get("/health")
def health(db: DbSession) -> JSONResponse:
    """Public, so a load balancer or a script can use it without logging in."""
    try:
        db.execute(select(1))
        database_ok = True
    except SQLAlchemyError:
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
