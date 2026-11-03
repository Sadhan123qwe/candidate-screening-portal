"""SQLAlchemy tables. The schema itself is created only by Alembic migrations.

match_label is deliberately absent. It is an offline training target, not
something a recruiter or the portal should ever see or edit.
"""

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates
from sqlalchemy.types import TypeDecorator


class ApplicationStatus(StrEnum):
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    REJECTED = "Rejected"


class PredictionLabel(StrEnum):
    POTENTIAL_MATCH = "Potential Match"
    NEEDS_REVIEW = "Needs Review"


class SkillKind(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STATUS_CHANGE = "status_change"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Guarantee timezone-aware UTC on the way in and out.

    SQLite has no timezone support and returns naive datetimes, so without this
    the same column would behave differently on SQLite and PostgreSQL.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime refused: all timestamps must be timezone-aware UTC")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    # Named constraints can be referred to by later migrations.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(32), default="recruiter", server_default="recruiter")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    @validates("email")
    def _lowercase_email(self, _key: str, value: str) -> str:
        return value.lower()


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)

    @validates("name")
    def _lowercase_name(self, _key: str, value: str) -> str:
        return value.lower()


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (CheckConstraint("min_experience_years >= 0", name="min_experience_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str | None] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    min_experience_years: Mapped[float] = mapped_column(Float, default=0)
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # version_id_col adds "WHERE version = <loaded>" to every UPDATE and raises if no
    # row matched, so two simultaneous writers cannot overwrite each other.
    __mapper_args__ = {"version_id_col": version}

    # selectin loading avoids one extra query per row when listing many records.
    skill_links: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="job")

    def _skill_names(self, kind: SkillKind) -> list[str]:
        return sorted(link.skill.name for link in self.skill_links if link.kind == kind)

    @property
    def required_skill_names(self) -> list[str]:
        return self._skill_names(SkillKind.REQUIRED)

    @property
    def preferred_skill_names(self) -> list[str]:
        return self._skill_names(SkillKind.PREFERRED)


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (CheckConstraint("experience_years >= 0", name="experience_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str | None] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    profile_summary: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __mapper_args__ = {"version_id_col": version}

    skill_links: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="selectin"
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="candidate")

    @validates("email")
    def _lowercase_email(self, _key: str, value: str) -> str:
        return value.lower()

    @property
    def skill_names(self) -> list[str]:
        return sorted(link.skill.name for link in self.skill_links)


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (CheckConstraint("kind IN ('required', 'preferred')", name="kind_allowed"),)

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))

    job: Mapped[Job] = relationship(back_populates="skill_links")
    skill: Mapped[Skill] = relationship(lazy="joined", innerjoin=True)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)

    candidate: Mapped[Candidate] = relationship(back_populates="skill_links")
    skill: Mapped[Skill] = relationship(lazy="joined", innerjoin=True)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        # Duplicate prevention lives here, in the database. App code alone could not
        # stop two simultaneous requests that both see "no existing application".
        UniqueConstraint("candidate_id", "job_id", name="uq_applications_candidate_job"),
        CheckConstraint("status IN ('Applied', 'Shortlisted', 'Rejected')", name="status_allowed"),
        Index("ix_applications_job_id", "job_id"),
        Index("ix_applications_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str | None] = mapped_column(String(32), unique=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(16), default=ApplicationStatus.APPLIED.value, server_default="Applied")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __mapper_args__ = {"version_id_col": version}

    candidate: Mapped[Candidate] = relationship(back_populates="applications", lazy="selectin")
    job: Mapped[Job] = relationship(back_populates="applications", lazy="selectin")
    prediction: Mapped["Prediction | None"] = relationship(
        back_populates="application", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="application", order_by="StatusHistory.changed_at, StatusHistory.id"
    )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("label IN ('Potential Match', 'Needs Review')", name="label_allowed"),
        CheckConstraint("probability >= 0 AND probability <= 1", name="probability_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), unique=True)
    label: Mapped[str] = mapped_column(String(32))
    probability: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(64))
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    application: Mapped[Application] = relationship(back_populates="prediction")


class StatusHistory(Base):
    __tablename__ = "status_history"
    __table_args__ = (Index("ix_status_history_application_id", "application_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    old_status: Mapped[str] = mapped_column(String(16))
    new_status: Mapped[str] = mapped_column(String(16))
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    application: Mapped[Application] = relationship(back_populates="history")
    changed_by: Mapped[User] = relationship(lazy="joined")


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(32))
    before_json: Mapped[dict | None] = mapped_column(JSON)
    after_json: Mapped[dict | None] = mapped_column(JSON)
    # Null means the system did it (the seed script), not a recruiter.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
