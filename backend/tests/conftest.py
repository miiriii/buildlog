import os
import secrets
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.db.session import create_db_engine

# Never require or display a developer's actual secret for tests.
os.environ["APP_ENV"] = "test"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "unit-test-placeholder-never-use-for-network"
os.environ["ANALYSIS_ENABLED"] = "false"


@pytest.fixture
def db_engine(tmp_path):
    engine = create_db_engine(f"sqlite+pysqlite:///{(tmp_path / 'test.sqlite3').as_posix()}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def password():
    return secrets.token_urlsafe(24)
