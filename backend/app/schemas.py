"""Pydantic request and response models. All server-side validation rules live here."""

import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator

from app.models import ApplicationStatus

SKILL_PATTERN = re.compile(r"[a-z0-9.+#-]+")


def _clean_skills(values: list[str]) -> list[str]:
    """Trim, lowercase and de-duplicate, keeping the order the user typed."""
    cleaned: list[str] = []
    for value in values:
        skill = value.strip().lower()
        if not SKILL_PATTERN.fullmatch(skill):
            raise ValueError(f"Invalid skill '{value}'. Use only letters, numbers and . + # -")
        if skill not in cleaned:
            cleaned.append(skill)
    return cleaned


SkillList = Annotated[list[Annotated[str, StringConstraints(max_length=64)]], Field(max_length=100), AfterValidator(_clean_skills)]
AtLeastOneSkill = Annotated[SkillList, Field(min_length=1)]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
# allow_inf_nan=False matters: Python's JSON parser accepts NaN, and NaN passes neither check.
ExperienceYears = Annotated[float, Field(ge=0, le=50, allow_inf_nan=False)]


def _reject_skill_overlap(required: list[str] | None, preferred: list[str] | None) -> None:
    both = sorted(set(required or []) & set(preferred or []))
    if both:
        raise ValueError(f"A skill can't be both required and preferred: {', '.join(both)}")


class RequestModel(BaseModel):
    # Unknown fields are refused, so a client can't send created_at or a status
    # and believe it was accepted. Timestamps are always set by the server.
    model_config = ConfigDict(extra="forbid")


# --- Auth ---


class LoginRequest(RequestModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Jobs ---


class JobCreate(RequestModel):
    title: ShortName
    description: LongText = ""
    min_experience_years: ExperienceYears = 0
    required_skills: AtLeastOneSkill
    preferred_skills: SkillList = []

    @model_validator(mode="after")
    def _check_skill_overlap(self) -> "JobCreate":
        _reject_skill_overlap(self.required_skills, self.preferred_skills)
        return self


class JobUpdate(RequestModel):
    version: int
    title: ShortName | None = None
    description: LongText | None = None
    min_experience_years: ExperienceYears | None = None
    required_skills: AtLeastOneSkill | None = None
    preferred_skills: SkillList | None = None

    @model_validator(mode="after")
    def _check_skill_overlap(self) -> "JobUpdate":
        _reject_skill_overlap(self.required_skills, self.preferred_skills)
        return self


class ApplicationCounts(BaseModel):
    Applied: int = 0
    Shortlisted: int = 0
    Rejected: int = 0


class JobOut(BaseModel):
    id: int
    external_ref: str | None
    title: str
    description: str
    min_experience_years: float
    required_skills: list[str]
    preferred_skills: list[str]
    version: int
    created_at: datetime
    updated_at: datetime
    application_counts: ApplicationCounts


class JobSummaryOut(BaseModel):
    job_id: int
    applied: int
    shortlisted: int
    rejected: int
    # Null when no model is loaded, because stored labels can't be trusted then.
    potential_match: int | None


# --- Candidates ---


class CandidateCreate(RequestModel):
    name: ShortName
    email: Email
    experience_years: ExperienceYears
    profile_summary: LongText = ""
    skills: AtLeastOneSkill


class CandidateUpdate(RequestModel):
    version: int
    name: ShortName | None = None
    email: Email | None = None
    experience_years: ExperienceYears | None = None
    profile_summary: LongText | None = None
    skills: AtLeastOneSkill | None = None


class CandidateOut(BaseModel):
    id: int
    external_ref: str | None
    name: str
    email: str
    experience_years: float
    profile_summary: str
    skills: list[str]
    version: int
    created_at: datetime
    updated_at: datetime
    application_count: int = 0


# --- Applications ---


class ApplicationCreate(RequestModel):
    candidate_id: int
    job_id: int


class StatusUpdate(RequestModel):
    status: ApplicationStatus
    version: int


class PredictionOut(BaseModel):
    label: str
    probability: float
    model_version: str
    computed_at: datetime


class FeatureContributionOut(BaseModel):
    feature: str
    value: float
    contribution: float


class ApplicationOut(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str
    candidate_experience_years: float
    job_id: int
    job_title: str
    required_matched: int
    required_total: int
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    # Null when no model is loaded. prediction_message then explains why.
    prediction: PredictionOut | None
    prediction_message: str | None


class ApplicationDetail(ApplicationOut):
    top_features: list[FeatureContributionOut]
    candidate_profile_summary: str
    job_min_experience_years: float
    experience_gap: float
    required_skills_matched: list[str]
    required_skills_missing: list[str]
    preferred_skills_matched: list[str]
    preferred_skills_missing: list[str]
    other_candidate_skills: list[str]
    imported_from_dataset: bool


class ApplicationPage(BaseModel):
    items: list[ApplicationOut]
    total: int
    page: int
    page_size: int


class ApplicationSummary(BaseModel):
    total: int
    applied: int
    shortlisted: int
    rejected: int


class PortalStats(BaseModel):
    jobs: int
    candidates: int
    applications: int


class CandidateDetail(CandidateOut):
    applications: list[ApplicationOut]


class StatusHistoryOut(BaseModel):
    id: int
    old_status: str
    new_status: str
    changed_by_user_id: int
    changed_by_name: str
    changed_at: datetime
