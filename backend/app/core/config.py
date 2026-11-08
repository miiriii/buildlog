from pathlib import Path
from typing import Literal
from urllib.parse import unquote

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: SecretStr
    database_url: SecretStr = SecretStr("")
    cors_origins: list[str] = ["http://localhost:5173"]
    session_cookie_name: str = "buildlog_session"
    session_max_age_seconds: int = 28800
    session_cookie_secure: bool = False
    openai_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    openai_model: str = "gpt-6-luna"
    analysis_enabled: bool = True
    analysis_poll_seconds: float = Field(default=2, gt=0, le=60)
    analysis_job_seconds: float = Field(default=75, gt=0, le=75)
    analysis_lease_seconds: int = Field(default=90, ge=90, le=300)

    @model_validator(mode="after")
    def validate_settings(self):
        if len(self.secret_key.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        if not self.cors_origins or any(
            origin == "*"
            or not origin.startswith(("http://", "https://"))
            or origin.endswith("/")
            for origin in self.cors_origins
        ):
            raise ValueError("CORS_ORIGINS must contain explicit origins without trailing slashes")
        if self.session_max_age_seconds <= 0:
            raise ValueError("Session lifetime must be positive")

        database_url = self.database_url.get_secret_value()
        if not database_url.strip():
            raise ValueError(
                "DATABASE_URL is required in backend/.env. Use the Supabase Session "
                "pooler connection (port 5432); SQLite fallback is disabled."
            )
        sqlite_prefix = next(
            (prefix for prefix in ("sqlite+pysqlite:///", "sqlite:///")
             if database_url.startswith(prefix)),
            None,
        )
        if sqlite_prefix:
            if self.app_env != "test":
                raise ValueError("PostgreSQL is required; SQLite is allowed only in isolated tests")
            # SQLAlchemy renders Windows drive separators as URI-encoded colons.
            database_path = unquote(database_url[len(sqlite_prefix):])
            if database_path != ":memory:":
                path = Path(database_path)
                if not path.is_absolute():
                    path = PROJECT_ROOT / path
                self.database_url = SecretStr(f"{sqlite_prefix}{path.resolve().as_posix()}")
        else:
            # Never include parser exceptions or raw input in configuration errors.
            try:
                url = make_url(database_url)
                valid = (
                    url.drivername in ("postgresql", "postgresql+psycopg")
                    and bool(url.host and url.database and url.username and url.password)
                    and (url.port is None or 1 <= url.port <= 65535)
                )
                if url.host and url.host.endswith(".pooler.supabase.com"):
                    valid = valid and url.port == 5432
                valid = valid and url.query.get("sslmode", "require") in (
                    "require", "verify-ca", "verify-full",
                )
            except Exception:
                valid = False
            if not valid:
                raise ValueError(
                    "Check DATABASE_URL in backend/.env: PostgreSQL Session pooler "
                    "host, port 5432, database, user, URL-encoded database password "
                    "and sslmode=require. Do not use an API key."
                )
        if self.app_env == "production":
            if not self.session_cookie_secure:
                raise ValueError("Production requires secure session cookies")
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production requires HTTPS origins")
        return self
