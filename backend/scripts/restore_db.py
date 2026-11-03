"""Restore a backup. Stop the server first. Run from backend/:

    python -m scripts.restore_db storage\\backups\\app-20260101-120000.db
"""

import argparse
import sys
from pathlib import Path

from app.config import get_settings
from app.services.backup import BackupError, DatabaseLockedError, restore_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore the database from a backup file.")
    parser.add_argument("backup_file", type=Path, help="Path to the backup .db file")
    args = parser.parse_args()

    db_path = get_settings().sqlite_path
    if db_path is None:
        print("Restore is for SQLite only. For PostgreSQL, use pg_restore.", file=sys.stderr)
        return 1

    try:
        safety_backup = restore_database(args.backup_file, db_path)
    except (BackupError, DatabaseLockedError) as error:
        print(f"Restore refused: {error}", file=sys.stderr)
        return 1

    if safety_backup is not None:
        print(f"The previous database was saved to {safety_backup}")
    print(f"Restored {db_path} from {args.backup_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
