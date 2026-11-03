"""Alembic environment: migrations use the same database URL as the app."""

from logging.config import fileConfig

from alembic import context

from app.db import build_engine
from app.config import get_settings
from app.models import Base

config = context.config
target_metadata = Base.metadata

# When the server runs migrations, it passes a connection and keeps its own logging setup.
connection = config.attributes.get("connection")
if connection is None and config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _configure_and_run(active_connection) -> None:
    context.configure(
        connection=active_connection,
        target_metadata=target_metadata,
        # SQLite cannot alter most constraints in place. Batch mode rebuilds the table,
        # and it is a harmless no-op on PostgreSQL.
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if connection is not None:
    _configure_and_run(connection)
else:
    engine = build_engine(get_settings().resolved_database_url)
    with engine.connect() as new_connection:
        _configure_and_run(new_connection)
        new_connection.commit()
    engine.dispose()
