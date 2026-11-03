"""Application errors and the single JSON error shape: {"detail": "...", "code": "..."}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """An expected failure that maps directly to an HTTP response."""

    def __init__(self, status_code: int, code: str, detail: str, headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.headers = headers


def not_found(entity: str) -> AppError:
    return AppError(404, f"{entity.upper()}_NOT_FOUND", f"{entity.capitalize()} not found.")


def stale_update() -> AppError:
    return AppError(409, "STALE_UPDATE", "This record was changed by someone else. Please review the latest version.")


def _error_body(detail: str, code: str, **extra) -> dict:
    return {"detail": detail, "code": code, **extra}


async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(_error_body(exc.detail, exc.code), status_code=exc.status_code, headers=exc.headers)


async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Built by hand because Pydantic's raw errors can contain objects JSON cannot encode.
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"].removeprefix("Value error, "),
        }
        for error in exc.errors()
    ]
    first = errors[0] if errors else {"field": "", "message": "Invalid request"}
    summary = f"{first['field']}: {first['message']}" if first["field"] else first["message"]
    return JSONResponse(_error_body(summary, "VALIDATION_ERROR", errors=errors), status_code=422)


async def _handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(_error_body(str(exc.detail), "HTTP_ERROR"), status_code=exc.status_code)


async def _handle_database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error", exc_info=exc)
    if isinstance(exc, OperationalError) and "locked" in str(exc).lower():
        # Nothing was saved, and trying again is safe.
        return JSONResponse(_error_body("The database is busy. Please try again.", "DB_BUSY"), status_code=503)
    return JSONResponse(_error_body("A database error occurred. Nothing was saved.", "DB_ERROR"), status_code=500)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(SQLAlchemyError, _handle_database_error)
