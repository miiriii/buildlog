"""Isolated databases only: materials metadata, migration and constraints."""
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.services import create_user
from app.db.session import create_db_engine
from app.materials.models import Material


@pytest.fixture
def owner(db_session, password):
    user = create_user(db_session, email="materials@example.com", nickname="자료주인", password=password)
    db_session.commit()
    return user


def values(owner_id):
    return dict(owner_id=owner_id, title="자료 제목", memo=None,
                original_filename="capture.png", stored_filename=f"{uuid.uuid4().hex}.png",
                media_type="image", mime_type="image/png", size_bytes=1)


def test_metadata_roundtrip_normalizes_title_and_empty_memo(db_session, owner):
    data = values(owner.id) | {"title": " \t공부  정리\n", "memo": ""}
    material = Material(**data)
    db_session.add(material)
    db_session.commit()
    assert material.title == "공부  정리"
    assert material.memo is None
    assert material.created_at is not None
    assert material.created_at.utcoffset().total_seconds() == 0
    material_id = material.id
    db_session.expire_all()
    stored = db_session.get(Material, material_id)
    assert stored.owner_id == owner.id
    assert stored.original_filename == "capture.png"
    assert stored.size_bytes == 1
    assert "공부" not in repr(stored)


@pytest.mark.parametrize("title", ["가", "가" * 100, "😀" * 100])
def test_title_and_memo_valid_boundaries(db_session, owner, title):
    material = Material(**(values(owner.id) | {"title": title, "memo": "😀" * 1000}))
    db_session.add(material)
    db_session.commit()
    assert material.title == title


@pytest.mark.parametrize("title", [None, "", " \t\n", "가" * 101])
def test_model_rejects_invalid_title(title):
    with pytest.raises(ValueError, match="title"):
        Material(**(values(1) | {"title": title}))


def test_model_rejects_long_memo():
    with pytest.raises(ValueError, match="memo"):
        Material(**(values(1) | {"memo": "가" * 1001}))


@pytest.mark.parametrize("overrides", [
    {"title": None}, {"title": ""}, {"title": " untrimmed "}, {"title": "가" * 101},
    {"memo": ""}, {"memo": "가" * 1001}, {"owner_id": None}, {"owner_id": 999999},
    {"original_filename": ""}, {"stored_filename": ""}, {"stored_filename": "x" * 256},
    {"media_type": "audio"}, {"mime_type": "text/plain"}, {"size_bytes": 0},
    {"size_bytes": -1}, {"size_bytes": 5242881},
    {"media_type": "image", "mime_type": "video/mp4"},
    {"media_type": "video", "mime_type": "image/png"},
    {"media_type": "video", "mime_type": "video/mp4", "size_bytes": 31457281},
])
def test_database_rejects_invalid_metadata_even_without_model_validation(db_session, owner, overrides):
    # Core SQL deliberately bypasses @validates so DB constraints are exercised.
    with pytest.raises(IntegrityError):
        db_session.execute(Material.__table__.insert().values(**(values(owner.id) | overrides)))
    db_session.rollback()


@pytest.mark.parametrize("kind,mime,size", [
    ("image", "image/png", 5242880), ("image", "image/jpeg", 5242880),
    ("video", "video/mp4", 31457280),
])
def test_database_accepts_exact_file_size_limits(db_session, owner, kind, mime, size):
    material = Material(**(values(owner.id) | {"media_type": kind, "mime_type": mime, "size_bytes": size}))
    db_session.add(material)
    db_session.commit()
    assert material.id


def test_storage_names_are_unique_and_user_delete_cannot_orphan_files(db_session, owner):
    data = values(owner.id)
    db_session.add(Material(**data))
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.execute(Material.__table__.insert().values(**data))
    db_session.rollback()
    with pytest.raises(IntegrityError):
        db_session.execute(User.__table__.delete().where(User.id == owner.id))
    db_session.rollback()


def test_schema_matches_model_and_has_ownership_index(db_engine):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)
        schema = inspect(connection)
        assert {column["name"] for column in schema.get_columns("materials")} == {
            "id", "owner_id", "title", "memo", "original_filename", "stored_filename",
            "media_type", "mime_type", "size_bytes", "created_at",
            "analysis_status", "analysis_summary", "analysis_error_code", "analysis_model",
            "analysis_prompt_version", "analysis_started_at", "analysis_completed_at", "analysis_job_token",
            "analysis_lease_expires_at", "analysis_attempt_count", "analysis_version",
            "analysis_input_tokens", "analysis_output_tokens", "analysis_metadata",
        }
        index = next(item for item in schema.get_indexes("materials") if item["name"] == "ix_materials_owner_created_id")
        assert index["column_names"] == ["owner_id", "created_at", "id"]
        assert schema.get_foreign_keys("materials")[0]["referred_table"] == "users"


def test_upgrade_repeat_and_down_up_preserve_existing_users(tmp_path, password):
    engine = create_db_engine(f"sqlite+pysqlite:///{(tmp_path / 'migration.sqlite3').as_posix()}")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "0001_users")
        with Session(engine) as session:
            user = create_user(session, email="preserve@example.com", nickname="회원보존", password=password)
            session.commit()
            expected = (user.id, user.email, user.nickname, user.password_hash)
        for revision in ["head", "head", "0001_users", "head"]:
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                if revision == "0001_users":
                    command.downgrade(config, revision)
                    assert "materials" not in inspect(connection).get_table_names()
                else:
                    command.upgrade(config, revision)
                    assert connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0003_material_analysis"
                actual = connection.execute(select(User.id, User.email, User.nickname, User.password_hash)).one()
                assert tuple(actual) == expected
    finally:
        engine.dispose()
