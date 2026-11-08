import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.accounts.models import User
from app.accounts.services import create_user, get_user_by_email
from app.core.security import hash_password, verify_password
from app.db.session import normalize_database_url


def test_create_and_find_user_with_email(db_session, password):
    user = create_user(db_session, email="  Learner@Example.COM  ", nickname="  빌드_로그  ", password=password)
    db_session.commit()
    assert user.id is not None
    assert user.email == "learner@example.com"
    assert user.nickname == "빌드_로그"
    assert user.is_admin is False
    assert get_user_by_email(db_session, "LEARNER@example.com").id == user.id
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(password, user.password_hash)
    assert not verify_password(secrets.token_urlsafe(24), user.password_hash)
    stored = db_session.execute(text("SELECT password_hash FROM users WHERE id = :id"), {"id": user.id}).scalar_one()
    assert not secrets.compare_digest(stored, password)
    assert password not in repr(user)


def test_different_users_can_be_saved(db_session, password):
    create_user(db_session, email="one@example.com", nickname="첫번째", password=password)
    create_user(db_session, email="two@example.com", nickname="두번째", password=password)
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(User)) == 2


@pytest.mark.parametrize("duplicate_field", ["email", "nickname"])
def test_database_blocks_duplicates(db_session, password, duplicate_field):
    first = create_user(db_session, email="one@example.com", nickname="공부하기", password=password)
    db_session.commit()
    duplicate = {
        "email": "two@example.com", "nickname": "다른닉네임",
        "password_hash": first.password_hash, "is_admin": False,
    }
    duplicate[duplicate_field] = getattr(first, duplicate_field)
    with pytest.raises(IntegrityError):
        # Core SQL bypasses model validation: uniqueness must still be enforced by DB.
        db_session.execute(User.__table__.insert().values(**duplicate))
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(User)) == 1


def test_email_case_is_normalized_before_unique_check(db_session, password):
    create_user(db_session, email="one@example.com", nickname="첫번째", password=password)
    db_session.commit()
    with pytest.raises(IntegrityError):
        create_user(db_session, email=" ONE@EXAMPLE.COM ", nickname="두번째", password=password)
    db_session.rollback()


@pytest.mark.parametrize("nickname", ["가", "가" * 21, "", "   ", "두 글자", "hello!", "🙂🙂"])
def test_invalid_nickname_is_rejected(db_session, password, nickname):
    with pytest.raises(ValueError, match="Nickname"):
        create_user(db_session, email="one@example.com", nickname=nickname, password=password)
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("nickname", ["가나", "가" * 20, "AB_12", "ㄱㄴ"])
def test_nickname_boundaries_and_allowed_letters(db_session, password, nickname):
    user = create_user(db_session, email="one@example.com", nickname=nickname, password=password)
    assert user.nickname == nickname


@pytest.mark.parametrize("email", ["", "   ", "invalid", "one@", None])
def test_missing_or_invalid_email_is_rejected(db_session, password, email):
    with pytest.raises(ValueError, match="[Ee]mail"):
        create_user(db_session, email=email, nickname="학습자", password=password)


@pytest.mark.parametrize("length", [7, 65])
def test_password_length_is_checked_before_hashing(db_session, length):
    password = secrets.token_hex(40)[:length]
    with pytest.raises(ValueError, match="8 to 64"):
        create_user(db_session, email="one@example.com", nickname="학습자", password=password)


@pytest.mark.parametrize("length", [8, 64])
def test_password_boundaries_are_accepted(length):
    password = secrets.token_hex(40)[:length]
    assert verify_password(password, hash_password(password))


def test_password_whitespace_is_preserved(password):
    password_with_spaces = f" {password} "
    encoded = hash_password(password_with_spaces)
    assert verify_password(password_with_spaces, encoded)
    assert not verify_password(password, encoded)


def test_same_password_uses_different_salts(password):
    assert hash_password(password) != hash_password(password)


def test_model_rejects_missing_required_fields_and_plaintext(db_session, password):
    with pytest.raises(ValueError, match="Argon2id"):
        User(email="one@example.com", nickname="학습자", password_hash=password)
    db_session.add(User(email="one@example.com", password_hash=hash_password(password)))
    with pytest.raises(ValueError, match="Nickname is required"):
        db_session.flush()
    db_session.rollback()


def test_public_creation_cannot_request_admin(db_session, password):
    with pytest.raises(TypeError):
        create_user(db_session, email="one@example.com", nickname="학습자", password=password, is_admin=True)
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


def test_database_enforces_required_fields_and_nickname_length(db_session, password):
    encoded = hash_password(password)
    for nickname in (None, "가", "가" * 21):
        with pytest.raises(IntegrityError):
            db_session.execute(User.__table__.insert().values(
                email="one@example.com", nickname=nickname, password_hash=encoded,
            ))
        db_session.rollback()


def test_database_also_rejects_plaintext_password_storage(db_session, password):
    with pytest.raises(IntegrityError):
        db_session.execute(User.__table__.insert().values(
            email="one@example.com", nickname="학습자", password_hash=password,
        ))
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


def test_foreign_keys_are_enabled_on_every_connection(db_engine):
    with db_engine.connect() as first, db_engine.connect() as second:
        assert first.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert second.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    with db_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE reference_check (user_id INTEGER REFERENCES users(id))")
    with pytest.raises(IntegrityError):
        with db_engine.begin() as connection:
            connection.exec_driver_sql("INSERT INTO reference_check (user_id) VALUES (9999)")


def test_migration_matches_models_and_is_repeatable(db_engine):
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        command.check(config)
        assert inspect(connection).get_table_names() == ["alembic_version", "materials", "users"]
        assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0003_material_analysis"


def test_committed_user_survives_new_process(db_engine, password):
    with Session(db_engine) as session, session.begin():
        create_user(session, email="persist@example.com", nickname="다시시작", password=password)
    db_engine.dispose()
    script = """
import sys
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.accounts.models import User
from app.db.session import create_db_engine
engine = create_db_engine(sys.argv[1])
with Session(engine) as session:
    print(session.scalar(select(func.count()).select_from(User)))
engine.dispose()
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, db_engine.url.render_as_string()],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "1"


def test_schema_also_compiles_for_postgresql_without_connecting():
    ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE users" in ddl
    assert "uq_users_email" in ddl
    assert "uq_users_nickname" in ddl
    assert "DEFAULT false" in ddl
    assert normalize_database_url("postgresql://localhost/buildlog").drivername == "postgresql+psycopg"
