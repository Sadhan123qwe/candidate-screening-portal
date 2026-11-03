"""Backups, restores, and refusing to start on a damaged database."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import build_engine
from app.models import Skill
from app.services import backup as backup_service
from app.services.backup import BackupError, DatabaseLockedError, backup_database, restore_database
from app.services.startup import prepare_storage, run_migrations


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "storage" / "app.db"


@pytest.fixture
def engine_for(db_path):
    engine = build_engine(f"sqlite:///{db_path.as_posix()}")
    run_migrations(engine)
    yield engine
    engine.dispose()


def _add_skill(engine, name: str) -> None:
    with Session(engine) as db, db.begin():
        db.add(Skill(name=name))


def _skill_names(engine) -> set[str]:
    with Session(engine) as db:
        return set(db.scalars(select(Skill.name)))


def test_restore_returns_the_data_to_the_backup(db_path, engine_for):
    _add_skill(engine_for, "kept")
    backup_path = backup_database(db_path)

    _add_skill(engine_for, "added-after-backup")
    assert _skill_names(engine_for) == {"kept", "added-after-backup"}

    engine_for.dispose()  # The equivalent of stopping the server.
    restore_database(backup_path, db_path)

    assert _skill_names(engine_for) == {"kept"}


def test_restore_saves_the_current_database_first(db_path, engine_for):
    _add_skill(engine_for, "kept")
    backup_path = backup_database(db_path)
    _add_skill(engine_for, "would-be-lost")

    engine_for.dispose()
    safety_backup = restore_database(backup_path, db_path)

    assert safety_backup is not None and safety_backup.exists()
    safety_engine = build_engine(f"sqlite:///{safety_backup.as_posix()}")
    assert "would-be-lost" in _skill_names(safety_engine)
    safety_engine.dispose()


def test_backup_taken_while_connections_are_open_includes_recent_commits(db_path, engine_for):
    # This commit may exist only in the WAL file. A plain file copy could miss it.
    _add_skill(engine_for, "recent-commit")

    backup_path = backup_database(db_path)

    backup_engine = build_engine(f"sqlite:///{backup_path.as_posix()}")
    assert "recent-commit" in _skill_names(backup_engine)
    backup_engine.dispose()


def test_restore_refuses_while_the_database_is_in_use(db_path, engine_for):
    _add_skill(engine_for, "kept")
    backup_path = backup_database(db_path)
    _add_skill(engine_for, "still-here")

    # engine_for holds an idle pooled connection, just like a running server.
    with pytest.raises(DatabaseLockedError):
        restore_database(backup_path, db_path)

    assert _skill_names(engine_for) == {"kept", "still-here"}


def test_restore_refuses_a_file_that_is_not_a_database(db_path, engine_for, tmp_path):
    _add_skill(engine_for, "kept")
    engine_for.dispose()
    not_a_database = tmp_path / "garbage.db"
    not_a_database.write_bytes(b"this is not a sqlite file" * 100)

    with pytest.raises(BackupError):
        restore_database(not_a_database, db_path)

    assert _skill_names(engine_for) == {"kept"}


def test_backup_of_a_missing_database_fails_clearly(tmp_path):
    missing = tmp_path / "nothing-here.db"
    with pytest.raises(BackupError):
        backup_database(missing)
    assert not missing.exists()  # It must not leave an empty database behind.


def test_startup_backup_keeps_only_the_last_ten_automatic_ones(db_path, engine_for, monkeypatch):
    manual_backup = backup_database(db_path)
    names = [f"app-auto-20260101-0000{number:02d}.db" for number in range(15)]
    directory = backup_service.backups_dir_for(db_path)
    for name in names:
        (directory / name).write_bytes(b"")

    backup_service.prune_automatic_backups(db_path)

    remaining = sorted(path.name for path in directory.glob("app-auto-*.db"))
    assert remaining == names[-10:]
    assert manual_backup.exists()  # Manual backups are never removed automatically.


def test_startup_backs_up_an_existing_database(db_path, engine_for):
    _add_skill(engine_for, "kept")

    prepare_storage(engine_for)

    backups = list(backup_service.backups_dir_for(db_path).glob("app-auto-*.db"))
    assert len(backups) == 1
    assert _skill_names(engine_for) == {"kept"}


def test_startup_stops_on_a_damaged_database(tmp_path):
    damaged = tmp_path / "damaged.db"
    damaged.write_bytes(b"this is not a sqlite file" * 100)
    engine = build_engine(f"sqlite:///{damaged.as_posix()}")

    with pytest.raises(BackupError):
        prepare_storage(engine)

    engine.dispose()


def test_startup_creates_a_missing_storage_folder(tmp_path):
    db_path = tmp_path / "does" / "not" / "exist" / "app.db"
    engine = build_engine(f"sqlite:///{db_path.as_posix()}")

    prepare_storage(engine)

    assert db_path.exists()
    engine.dispose()
