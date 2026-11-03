"""SQLite backup and restore, shared by the server's startup and the CLI scripts.

Everything goes through SQLite's online backup API rather than a file copy. A file
copy taken while the server runs could miss commits still in the WAL file, or catch
the database mid-write. The backup API always produces a consistent snapshot.
"""

import contextlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MANUAL_PREFIX = "app"
AUTOMATIC_PREFIX = "app-auto"
PRE_RESTORE_PREFIX = "app-prerestore"
AUTOMATIC_BACKUPS_TO_KEEP = 10


class BackupError(Exception):
    """The file is missing, damaged or not a SQLite database."""


class DatabaseLockedError(Exception):
    """Another process has the database open, so restoring now could corrupt it."""


def backups_dir_for(db_path: Path) -> Path:
    return db_path.parent / "backups"


def _timestamped_path(directory: Path, prefix: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = directory / f"{prefix}-{stamp}.db"
    # Two backups in the same second must not overwrite each other.
    counter = 1
    while path.exists():
        path = directory / f"{prefix}-{stamp}-{counter}.db"
        counter += 1
    return path


def _copy_database(source: Path, destination: Path) -> None:
    with contextlib.closing(sqlite3.connect(source)) as source_connection:
        with contextlib.closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)


def assert_healthy(path: Path) -> None:
    """Raise BackupError unless this is a readable, undamaged SQLite database."""
    if not path.is_file():
        raise BackupError(f"File not found: {path}")
    try:
        with contextlib.closing(sqlite3.connect(path)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.DatabaseError as error:
        raise BackupError(f"{path} is not a usable SQLite database: {error}") from error
    if result != "ok":
        raise BackupError(f"{path} failed its integrity check: {result}")


def backup_database(db_path: Path, prefix: str = MANUAL_PREFIX) -> Path:
    """Copy the database to a new timestamped file and return its path."""
    if not db_path.is_file():
        # sqlite3.connect would otherwise create an empty file and "back up" nothing.
        raise BackupError(f"Database file not found: {db_path}")

    directory = backups_dir_for(db_path)
    directory.mkdir(parents=True, exist_ok=True)
    destination = _timestamped_path(directory, prefix)

    # Write under a temporary name, so a crash can't leave a partial file that looks
    # like a real backup.
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        _copy_database(db_path, temporary)
        assert_healthy(temporary)
        temporary.replace(destination)
    except sqlite3.DatabaseError as error:
        raise BackupError(f"Could not back up {db_path}: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def prune_automatic_backups(db_path: Path, keep: int = AUTOMATIC_BACKUPS_TO_KEEP) -> None:
    """Delete old automatic backups only. Manual and pre-restore ones are never removed."""
    backups = sorted(backups_dir_for(db_path).glob(f"{AUTOMATIC_PREFIX}-*.db"))
    for old_backup in backups[:-keep]:
        old_backup.unlink()
        logger.info("Removed old automatic backup %s", old_backup.name)


def backup_on_startup(db_path: Path) -> Path:
    backup_path = backup_database(db_path, prefix=AUTOMATIC_PREFIX)
    prune_automatic_backups(db_path)
    return backup_path


def _refuse_if_locked(db_path: Path) -> None:
    """Refuse to restore while another process has the database open.

    A plain lock test isn't enough: in WAL mode an idle server holds no write lock,
    so BEGIN EXCLUSIVE would succeed even with the server running. Leaving WAL mode
    needs sole access to the file, which makes it a reliable test. Every connection
    the app opens switches back to WAL.
    """
    try:
        with contextlib.closing(sqlite3.connect(db_path, timeout=1)) as connection:
            journal_mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
    except sqlite3.OperationalError as error:
        raise DatabaseLockedError(f"{db_path} is in use. Stop the server and try again.") from error
    if journal_mode.lower() != "delete":
        raise DatabaseLockedError(f"{db_path} is in use. Stop the server and try again.")


def restore_database(backup_file: Path, db_path: Path) -> Path | None:
    """Replace the database with a backup, saving the current database first.

    Returns the safety backup's path, or None if there was no database to save.
    """
    # Check the backup before touching anything, so a bad file changes nothing.
    assert_healthy(backup_file)

    safety_backup = None
    if db_path.exists():
        _refuse_if_locked(db_path)
        safety_backup = backup_database(db_path, prefix=PRE_RESTORE_PREFIX)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    # The backup API writes in a transaction, so a crash here leaves the old database intact.
    _copy_database(backup_file, db_path)
    assert_healthy(db_path)
    return safety_backup
