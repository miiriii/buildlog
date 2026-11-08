from collections.abc import Generator

from fastapi import Request

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

def normalize_database_url(database_url: str) -> URL:
    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def create_db_engine(database_url: str) -> Engine:
    url = normalize_database_url(database_url)
    options = {"hide_parameters": True, "pool_pre_ping": True, "echo": False}
    if url.get_backend_name() == "postgresql":
        # Session pooler supports regular sessions. Require encrypted transport.
        options["connect_args"] = {
            "sslmode": url.query.get("sslmode", "require"),
            "connect_timeout": 10,
        }
    if url.get_backend_name() == "sqlite":
        # Modern transaction control also makes SQLite DDL transactional.
        options["connect_args"] = {"check_same_thread": False, "autocommit": False}
        if url.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            previous_autocommit = connection.autocommit
            connection.autocommit = True
            try:
                cursor = connection.cursor()
                try:
                    cursor.execute("PRAGMA foreign_keys=ON")
                finally:
                    cursor.close()
            finally:
                connection.autocommit = previous_autocommit
    return engine


def get_session(request: Request) -> Generator[Session, None, None]:
    # Creating tables remains an explicit Alembic operation, never a request side effect.
    with Session(request.app.state.db_engine, expire_on_commit=False) as session:
        yield session
