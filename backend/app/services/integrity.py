"""Database health checks, used by scripts/check_db.py and by server startup."""

from dataclasses import dataclass, field

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, aliased

from app.ml import predictor as predictor_module
from app.models import Application, Base, Candidate, Job, Prediction


@dataclass
class IntegrityReport:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.problems


def check_engine_health(db: Session) -> list[str]:
    """Low-level checks. These run at startup and must pass before serving requests."""
    if db.get_bind().dialect.name != "sqlite":
        db.execute(select(1))  # PostgreSQL checks its own pages; confirm it answers.
        return []

    problems = []
    # Fixed PRAGMA statements with no user input: there is nothing here to inject.
    integrity = [row[0] for row in db.execute(text("PRAGMA integrity_check"))]
    if integrity != ["ok"]:
        problems.append(f"integrity_check failed: {'; '.join(integrity)}")
    violations = db.execute(text("PRAGMA foreign_key_check")).all()
    if violations:
        problems.append(f"foreign_key_check found {len(violations)} violation(s)")
    return problems


def _count_rows(db: Session) -> dict[str, int]:
    return {table.name: db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}


def _find_orphans(db: Session) -> list[str]:
    """Check every foreign key, on any database, by reading them from the models."""
    problems = []
    for table in Base.metadata.sorted_tables:
        for foreign_key in table.foreign_keys:
            parent_column = foreign_key.column
            orphans = db.scalar(
                select(func.count())
                .select_from(table.outerjoin(parent_column.table, foreign_key.parent == parent_column))
                .where(foreign_key.parent.is_not(None), parent_column.is_(None))
            )
            if orphans:
                problems.append(f"{orphans} orphan row(s) in {table.name}.{foreign_key.parent.name}")
    return problems


def _find_active_applications_with_deleted_parent(db: Session) -> list[str]:
    candidate, job = aliased(Candidate), aliased(Job)
    count = db.scalar(
        select(func.count())
        .select_from(Application)
        .join(candidate, Application.candidate_id == candidate.id)
        .join(job, Application.job_id == job.id)
        .where(
            Application.deleted_at.is_(None),
            (candidate.deleted_at.is_not(None)) | (job.deleted_at.is_not(None)),
        )
    )
    return [f"{count} active application(s) point at a deleted candidate or job"] if count else []


def _find_applications_without_prediction(db: Session) -> list[str]:
    count = db.scalar(
        select(func.count())
        .select_from(Application)
        .outerjoin(Prediction, Prediction.application_id == Application.id)
        .where(Application.deleted_at.is_(None), Prediction.id.is_(None))
    )
    return [f"{count} active application(s) have no stored prediction"] if count else []


def _find_old_model_predictions(db: Session) -> list[str]:
    current = predictor_module.get_predictor().model_version
    if current is None:
        return ["No model is loaded, so prediction versions were not compared."]
    count = db.scalar(select(func.count()).select_from(Prediction).where(Prediction.model_version != current))
    if count:
        return [f"{count} prediction(s) came from an older model. The next server start recomputes them."]
    return []


def run_all_checks(engine: Engine) -> IntegrityReport:
    with Session(engine) as db:
        report = IntegrityReport()
        report.problems.extend(check_engine_health(db))
        report.row_counts = _count_rows(db)
        report.problems.extend(_find_orphans(db))
        report.problems.extend(_find_active_applications_with_deleted_parent(db))
        report.problems.extend(_find_applications_without_prediction(db))
        report.warnings.extend(_find_old_model_predictions(db))
    return report
