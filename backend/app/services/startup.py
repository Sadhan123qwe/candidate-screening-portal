"""The fixed start-up sequence. Any failure stops the server.

Running on a broken database risks making the damage worse, so stopping with a
clear message is the safe choice.
"""

import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR, DEFAULT_JWT_SECRET, get_settings, sqlite_path_from_url
from app.db import engine as default_engine
from app.ml import predictor as predictor_module
from app.services.backup import backup_on_startup
from app.services.integrity import check_engine_health
from app.services.predictions import refresh_stale_predictions

logger = logging.getLogger(__name__)


class StartupError(Exception):
    pass


def run_migrations(engine: Engine) -> None:
    config = Config(BACKEND_DIR / "alembic.ini")
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def prepare_storage(engine: Engine = default_engine) -> None:
    db_path = sqlite_path_from_url(engine.url)

    # Step 1: make sure storage/ exists.
    if db_path is not None:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 2: back up first, so a bad migration can always be undone.
    if db_path is not None and db_path.exists():
        backup_path = backup_on_startup(db_path)
        logger.info("Backed up the database to %s", backup_path)

    # Step 3: bring the schema up to date.
    run_migrations(engine)

    # Step 4: refuse to serve from a database that fails its checks.
    with Session(engine) as db:
        problems = check_engine_health(db)
    if problems:
        raise StartupError("Database integrity check failed: " + "; ".join(problems))

    # Step 5: bring predictions up to date with the loaded model.
    predictor = predictor_module.get_predictor()
    if predictor.available:
        with Session(engine) as db, db.begin():
            refreshed = refresh_stale_predictions(db)
        logger.info("Model %s loaded. Recomputed %d prediction(s).", predictor.model_version, refreshed)
    else:
        logger.warning("Running without a model. Predictions will show as unavailable.")

    if get_settings().jwt_secret == DEFAULT_JWT_SECRET:
        logger.warning("JWT_SECRET is the development default. Set your own value outside local use.")
