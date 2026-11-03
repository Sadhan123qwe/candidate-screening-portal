"""Application factory: wires together startup, middleware, error handling and routers."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import engine
from app.errors import register_error_handlers
from app.routers import applications, auth, candidates, jobs, model
from app.services.startup import prepare_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        prepare_storage()
    except Exception:
        logger.critical("Startup stopped: the database is not safe to use. See the error below.", exc_info=True)
        raise
    yield
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Candidate Screening Portal", lifespan=lifespan)

    @app.middleware("http")
    async def return_json_for_unexpected_errors(request: Request, call_next):
        # This runs inside the CORS middleware. Starlette's own catch-all sits outside
        # it, so its 500s would lack CORS headers and the browser would hide the error.
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return JSONResponse({"detail": "Something went wrong. Nothing was saved.", "code": "INTERNAL_ERROR"}, 500)

    # Added last, so it wraps the handler above.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    for module in (auth, jobs, candidates, applications, model):
        app.include_router(module.router)
    return app


app = create_app()
