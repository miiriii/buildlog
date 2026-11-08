import secrets

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.core.config import PROJECT_ROOT, Settings
from app.main import create_app


def make_settings(**overrides):
    return Settings(
        _env_file=None,
        secret_key=SecretStr(secrets.token_urlsafe(48)),
        **overrides,
    )


def test_health_contains_only_public_status():
    with TestClient(create_app(make_settings())) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "BuildLog"}


def test_allowed_browser_origin_can_send_credentials():
    with TestClient(create_app(make_settings())) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-CSRF-Token",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unapproved_origin_has_no_browser_permission():
    with TestClient(create_app(make_settings())) as client:
        response = client.options(
            "/api/health",
            headers={"Origin": "https://unapproved.example", "Access-Control-Request-Method": "GET"},
        )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_sqlite_path_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = make_settings(database_url=SecretStr("sqlite+pysqlite:///./database/buildlog.sqlite3"))
    expected = (PROJECT_ROOT / "database/buildlog.sqlite3").as_posix()
    assert settings.database_url.get_secret_value() == f"sqlite+pysqlite:///{expected}"
    assert not list(tmp_path.iterdir())


def test_production_cannot_fall_back_to_local_database():
    with pytest.raises(ValidationError, match="PostgreSQL is required"):
        make_settings(app_env="production")


def test_cors_wildcard_is_rejected():
    with pytest.raises(ValidationError, match="explicit origins"):
        make_settings(cors_origins=["*"])


def test_blank_database_setting_does_not_fall_back(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    env_file = tmp_path / ".env"
    env_file.write_text("APP_ENV=\nDATABASE_URL=\nCORS_ORIGINS=\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="DATABASE_URL is required in backend/.env"):
        Settings(_env_file=env_file)


def test_settings_and_validation_errors_do_not_display_secrets():
    secret = secrets.token_urlsafe(48)
    settings = Settings(_env_file=None, secret_key=SecretStr(secret))
    assert secret not in repr(settings)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, secret_key=SecretStr(secret), cors_origins=["*"])
    assert secret not in str(error.value)


def test_uri_encoded_sqlite_path_keeps_the_same_project_database():
    from urllib.parse import quote

    path = (PROJECT_ROOT / "database/buildlog.sqlite3").as_posix()
    encoded = quote(path, safe="/")
    settings = make_settings(database_url=SecretStr(f"sqlite+pysqlite:///{encoded}"))
    assert settings.database_url.get_secret_value() == f"sqlite+pysqlite:///{path}"
