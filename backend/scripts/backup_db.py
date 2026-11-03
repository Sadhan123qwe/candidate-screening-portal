"""Take a backup. Safe while the server runs. Run from backend/: python -m scripts.backup_db"""

import sys

from app.config import get_settings
from app.services.backup import BackupError, backup_database


def main() -> int:
    db_path = get_settings().sqlite_path
    if db_path is None:
        print("Backups are for SQLite only. For PostgreSQL, use pg_dump.", file=sys.stderr)
        return 1
    try:
        backup_path = backup_database(db_path)
    except BackupError as error:
        print(f"Backup failed: {error}", file=sys.stderr)
        return 1
    print(f"Backup written to {backup_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
