"""Application settings, read from environment variables and backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_JWT_SECRET = "change-me-local-development-only-secret"


class Settings(BaseSettings):
    # An absolute path to .env, so the result does not depend on the current folder.
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "sqlite:///./storage/app.db"

    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    demo_user_email: str = "recruiter@demo.com"
    demo_user_password: str = "Demo@12345"

    artifact_path: Path = BACKEND_DIR / "artifacts" / "model.joblib"
    metrics_path: Path = BACKEND_DIR / "artifacts" / "metrics.json"
    data_dir: Path = BACKEND_DIR / "data"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_database_url(self) -> URL:
        return resolve_database_url(self.database_url)

    @property
    def sqlite_path(self) -> Path | None:
        return sqlite_path_from_url(self.resolved_database_url)


def resolve_database_url(database_url: str) -> URL:
    """Anchor a relative SQLite path to backend/.

    Otherwise, starting the server from another folder would silently create a
    second, empty database there, and recruiters would appear to lose their data.
    """
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        path = Path(url.database)
        if not path.is_absolute():
            url = url.set(database=str((BACKEND_DIR / path).resolve()))
    return url


def sqlite_path_from_url(url: URL) -> Path | None:
    """Return the database file path, or None when the database is not a SQLite file."""
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    return Path(url.database)


@lru_cache
def get_settings() -> Settings:
    return Settings()
