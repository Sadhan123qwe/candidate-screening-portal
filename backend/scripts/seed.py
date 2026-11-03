"""Import the dataset. Run from backend/: python -m scripts.seed

Safe to run repeatedly. Existing rows are only ever skipped, never changed, so a
recruiter's edits and status changes always survive a re-seed. match_label is never
read, because it is an offline training target rather than portal data.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import get_settings
from app.db import SessionLocal
from app.models import Application, ApplicationStatus, AuditAction, Candidate, Job, Skill, User
from app.services.audit import record_audit, snapshot_application, snapshot_candidate, snapshot_job
from app.services.candidates import set_candidate_skills
from app.services.jobs import set_job_skills
from app.services.predictions import refresh_stale_predictions
from app.services.skills import get_or_create_skills


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _split_skills(value: str) -> list[str]:
    return [skill for skill in value.split(";") if skill]


def _seed_demo_user(db: Session, counts: Counter) -> None:
    settings = get_settings()
    if db.scalar(select(User).where(User.email == settings.demo_user_email.lower())):
        counts["users skipped"] += 1
        return
    db.add(
        User(
            email=settings.demo_user_email,
            password_hash=hash_password(settings.demo_user_password),
            full_name="Demo Recruiter",
        )
    )
    db.flush()
    counts["users inserted"] += 1


def _seed_skills(db: Session, candidates: list[dict], jobs: list[dict], counts: Counter) -> None:
    names: set[str] = set()
    for row in candidates:
        names.update(_split_skills(row["skills"]))
    for row in jobs:
        names.update(_split_skills(row["required_skills"]))
        names.update(_split_skills(row["preferred_skills"]))
    already_stored = set(db.scalars(select(Skill.name))) & names
    get_or_create_skills(db, names)
    counts["skills inserted"] += len(names - already_stored)
    counts["skills skipped"] += len(already_stored)


def _seed_jobs(db: Session, rows: list[dict], counts: Counter) -> dict[str, Job]:
    jobs = {job.external_ref: job for job in db.scalars(select(Job).where(Job.external_ref.is_not(None)))}
    for row in rows:
        if row["job_id"] in jobs:
            counts["jobs skipped"] += 1
            continue
        job = Job(
            external_ref=row["job_id"],
            title=row["title"],
            description=row["description"],
            min_experience_years=float(row["minimum_experience_years"]),
        )
        db.add(job)
        db.flush()
        set_job_skills(db, job, _split_skills(row["required_skills"]), _split_skills(row["preferred_skills"]))
        db.flush()
        record_audit(db, "job", job.id, AuditAction.CREATE, None, snapshot_job(job), None)
        jobs[row["job_id"]] = job
        counts["jobs inserted"] += 1
    return jobs


def _seed_candidates(db: Session, rows: list[dict], counts: Counter) -> dict[str, Candidate]:
    existing = list(db.scalars(select(Candidate)))
    by_ref = {candidate.external_ref: candidate for candidate in existing if candidate.external_ref}
    used_emails = {candidate.email for candidate in existing}
    for row in rows:
        if row["candidate_id"] in by_ref:
            counts["candidates skipped"] += 1
            continue
        email = row["email"].lower()
        if email in used_emails:
            # A recruiter already created someone with this email. Leave their record alone.
            counts["candidates skipped (email already in use)"] += 1
            continue
        candidate = Candidate(
            external_ref=row["candidate_id"],
            name=row["name"],
            email=email,
            experience_years=float(row["experience_years"]),
            profile_summary=row["profile_summary"],
        )
        db.add(candidate)
        db.flush()
        set_candidate_skills(db, candidate, _split_skills(row["skills"]))
        db.flush()
        record_audit(db, "candidate", candidate.id, AuditAction.CREATE, None, snapshot_candidate(candidate), None)
        by_ref[row["candidate_id"]] = candidate
        used_emails.add(email)
        counts["candidates inserted"] += 1
    return by_ref


def _seed_applications(
    db: Session, rows: list[dict], candidates: dict[str, Candidate], jobs: dict[str, Job], counts: Counter
) -> None:
    existing = list(db.scalars(select(Application)))
    known_refs = {application.external_ref for application in existing}
    # A recruiter may have already created the same pair in the UI, with no external_ref.
    known_pairs = {(application.candidate_id, application.job_id) for application in existing}

    for row in rows:
        candidate = candidates.get(row["candidate_id"])
        job = jobs.get(row["job_id"])
        if row["application_id"] in known_refs:
            counts["applications skipped"] += 1
            continue
        # A recruiter's soft delete must stay deleted, so nothing is re-added beneath it.
        parent_missing = candidate is None or job is None
        if parent_missing or candidate.deleted_at is not None or job.deleted_at is not None:
            counts["applications skipped (candidate or job unavailable)"] += 1
            continue
        if (candidate.id, job.id) in known_pairs:
            counts["applications skipped (pair already exists)"] += 1
            continue

        # Every import starts as Applied. match_label must not become a recruiter decision.
        application = Application(
            external_ref=row["application_id"],
            candidate=candidate,
            job=job,
            status=ApplicationStatus.APPLIED.value,
        )
        db.add(application)
        db.flush()
        record_audit(db, "application", application.id, AuditAction.CREATE, None, snapshot_application(application), None)
        known_pairs.add((candidate.id, job.id))
        counts["applications inserted"] += 1


def seed_database(db: Session) -> Counter:
    """Import everything using the caller's session, so it can be one transaction."""
    data_dir = get_settings().data_dir
    candidate_rows = _read_csv(data_dir / "candidates.csv")
    job_rows = _read_csv(data_dir / "jobs.csv")
    application_rows = _read_csv(data_dir / "applications.csv")

    counts: Counter = Counter()
    _seed_demo_user(db, counts)
    _seed_skills(db, candidate_rows, job_rows, counts)
    jobs = _seed_jobs(db, job_rows, counts)
    candidates = _seed_candidates(db, candidate_rows, counts)
    _seed_applications(db, application_rows, candidates, jobs, counts)
    counts["predictions computed"] = refresh_stale_predictions(db)
    return counts


def main() -> int:
    try:
        # One transaction: a failure part-way leaves the database exactly as it was.
        with SessionLocal() as db, db.begin():
            counts = seed_database(db)
    except OperationalError as error:
        print(f"Seed failed: {error.orig}. Did you run 'alembic upgrade head' first?", file=sys.stderr)
        return 1

    print("Seed complete. Nothing is ever overwritten.")
    for name, count in sorted(counts.items()):
        print(f"  {name}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
