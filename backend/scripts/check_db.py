"""Verify the database. Exits non-zero on any problem. Run from backend/: python -m scripts.check_db"""

import sys

from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import engine
from app.services.integrity import run_all_checks


def main() -> int:
    db_path = get_settings().sqlite_path
    # Connecting would otherwise create an empty file and hide the real problem.
    if db_path is not None and not db_path.exists():
        print(f"FAIL: database file not found: {db_path}")
        return 1

    try:
        report = run_all_checks(engine)
    except SQLAlchemyError as error:
        print(f"FAIL: could not read the database. Have migrations run? {error}")
        return 1

    print("Row counts:")
    for table, count in report.row_counts.items():
        print(f"  {table}: {count}")
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for problem in report.problems:
        print(f"PROBLEM: {problem}")

    if report.ok:
        print("PASS: no problems found")
        return 0
    print(f"FAIL: {len(report.problems)} problem(s) found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
