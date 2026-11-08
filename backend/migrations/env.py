from alembic import context
from alembic.util import CommandError
from pydantic import ValidationError
from pydantic_settings import SettingsError
from sqlalchemy.exc import SQLAlchemyError

from app.accounts.models import User  # noqa: F401 — registers table metadata
from app.materials.models import Material  # noqa: F401 — registers table metadata
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_db_engine, normalize_database_url

config = context.config
target_metadata = Base.metadata


def migration_settings():
    try:
        return Settings()
    except (ValidationError, SettingsError):
        raise CommandError(
            "Invalid backend/.env. Set DATABASE_URL to the PostgreSQL Session pooler "
            "URI (port 5432, DB password URL-encoded, sslmode=require). "
            "Keep SECRET_KEY at least 32 characters and CORS_ORIGINS a JSON array "
            "of allowed origins. SQLite fallback is disabled."
        ) from None


def configure_connection(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=normalize_database_url(migration_settings().database_url.get_secret_value()),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    # Tests supply an isolated connection and never read a developer's DB URL.
    configure_connection(config.attributes["connection"])
else:
    engine = create_db_engine(migration_settings().database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            configure_connection(connection)
    except SQLAlchemyError:
        # Driver exceptions can include connection details. Do not print them.
        raise CommandError(
            "Database connection or migration failed. Check backend/.env: Session "
            "pooler host, port 5432, database name, user and URL-encoded DB password; "
            "check project status, network access, SSL and database permissions. "
            "No SQLite fallback was attempted. Do not share the full connection URL."
        ) from None
    finally:
        engine.dispose()
