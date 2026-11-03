"""Database engine, SQLite pragmas and the per-request session."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings, sqlite_path_from_url


def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Pragmas are per connection in SQLite, so they must run on every new connection."""
    cursor = dbapi_connection.cursor()
    # Set first, so the statements below also wait for a lock instead of failing.
    cursor.execute("PRAGMA busy_timeout=5000")
    # SQLite ignores foreign keys unless this is switched on.
    cursor.execute("PRAGMA foreign_keys=ON")
    # WAL lets readers continue while one writer commits.
    cursor.execute("PRAGMA journal_mode=WAL")
    # FULL syncs every commit to disk. WAL's common NORMAL setting can lose the last
    # commits on power failure, which would break the durability guarantee.
    cursor.execute("PRAGMA synchronous=FULL")
    cursor.close()


def build_engine(url: URL | str) -> Engine:
    """Create an engine. All SQLite-specific setup stays behind this dialect check."""
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        sqlite_path = sqlite_path_from_url(engine.url)
        if sqlite_path is not None:
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        event.listen(engine, "connect", _apply_sqlite_pragmas)
    return engine


engine = build_engine(get_settings().resolved_database_url)

# expire_on_commit=False keeps objects readable after a commit without another query.
SessionLocal = sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """One session per request: commit on success, roll back on any exception."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# scope="function" is what makes the durability guarantee true. FastAPI's default
# scope runs the code after `yield` once the response has been sent, so a client
# could be told 201 and the commit could still fail. With this scope, a failed
# commit becomes an error response. tests/test_atomicity.py proves it.
DbSession = Annotated[Session, Depends(get_db, scope="function")]
