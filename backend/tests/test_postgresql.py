"""No remote connections: configuration, driver options and migration regression."""
import io
import secrets
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import quote

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.util import CommandError
from pydantic import SecretStr, ValidationError
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.core.config import BACKEND_ROOT, Settings
from app.db import session as db


def postgres_url():
    # Synthetic credentials only. Never connect using this URL.
    password = secrets.token_urlsafe(24) + "@:/#%"
    url = db.URL.create(
        "postgresql", username="postgres.test", password=password,
        host="aws-0-test.pooler.supabase.com", port=5432, database="postgres",
    ).render_as_string(hide_password=False)
    return url, password


def settings_for(url, **kwargs):
    return Settings(
        _env_file=None, app_env="development",
        secret_key=SecretStr(secrets.token_urlsafe(48)),
        database_url=SecretStr(url), **kwargs,
    )


def test_backend_env_location_is_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Path(Settings.model_config["env_file"]) == BACKEND_ROOT / ".env"


@pytest.mark.parametrize("url", ["", "sqlite+pysqlite:///:memory:", "invalid", "postgresql://localhost/db"])
def test_runtime_requires_explicit_complete_postgresql_settings(url):
    with pytest.raises(ValidationError):
        settings_for(url)


def test_encoded_password_and_secret_are_preserved_but_never_displayed():
    url, password = postgres_url()
    settings = settings_for(url)
    assert make_url(settings.database_url.get_secret_value()).password == password
    assert password not in repr(settings)
    assert url not in repr(settings)
    with pytest.raises(ValidationError) as error:
        settings_for(url.replace(":5432/", ":6543/"))
    assert password not in str(error.value)
    assert quote(password, safe="") not in str(error.value)
    assert url not in str(error.value)
    assert "Session pooler" in str(error.value)


def test_runtime_rejects_unencrypted_connection():
    url, _ = postgres_url()
    with pytest.raises(ValidationError, match="sslmode=require"):
        settings_for(url + "?sslmode=disable")


def test_postgresql_engine_uses_psycopg_ssl_and_bounded_connection_time(monkeypatch):
    create = Mock()
    monkeypatch.setattr(db, "create_engine", create)
    url, _ = postgres_url()
    db.create_db_engine(settings_for(url).database_url.get_secret_value())
    args, options = create.call_args
    assert args[0].drivername == "postgresql+psycopg"
    assert options["hide_parameters"] is True
    assert options["echo"] is False
    assert options["pool_pre_ping"] is True
    assert options["connect_args"] == {"sslmode": "require", "connect_timeout": 10}


def test_alembic_compiles_postgresql_schema_without_any_connection(monkeypatch):
    def no_connection(*_args, **_kwargs):
        pytest.fail("Offline migrations must not open a connection")
    monkeypatch.setattr(psycopg, "connect", no_connection)
    url, _ = postgres_url()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", url)
    output = io.StringIO()
    config = Config(str(BACKEND_ROOT / "alembic.ini"), output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "CREATE TABLE alembic_version" in sql
    assert "uq_users_email" in sql and "uq_users_nickname" in sql
    assert "DEFAULT false" in sql
    assert "0001_users" in sql
    assert "CREATE TABLE materials" in sql
    assert "0002_materials" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "ix_materials_owner_created_id" in sql
    assert "REFERENCES users (id)" in sql
    assert "5242880" in sql and "31457280" in sql
    assert "ALTER TABLE materials ENABLE ROW LEVEL SECURITY" in sql
    assert "FROM PUBLIC" in sql and "FROM anon" in sql and "FROM authenticated" in sql
    assert "CREATE POLICY" not in sql
    assert "END;\n$$" in sql
    assert url not in sql


def test_alembic_failure_hides_driver_connection_details(monkeypatch):
    url, password = postgres_url()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", url)
    engine = Mock()
    engine.connect.side_effect = OperationalError(None, None, Exception(url))
    monkeypatch.setattr(db, "create_db_engine", Mock(return_value=engine))
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    with pytest.raises(CommandError) as error:
        command.upgrade(config, "head")
    assert "backend/.env" in str(error.value)
    assert password not in str(error.value)
    assert url not in str(error.value)
    assert error.value.__suppress_context__ is True
    engine.dispose.assert_called_once()
