"""Upload tests use isolated SQLite and tmp_path only; no real user files."""
import asyncio
import io
import secrets
import struct

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile
from starlette.requests import Request

from app.core.config import Settings
from app.main import create_app
from app.materials import router as material_router, storage
from app.materials.models import Material
from app.materials.schemas import MaterialInput
from app.materials.services import create_material

ORIGIN = "http://localhost:5173"


@pytest.fixture
def api(db_engine, tmp_path):
    settings = Settings(_env_file=None, app_env="test", secret_key=SecretStr(secrets.token_urlsafe(48)),
                        database_url=SecretStr(db_engine.url.render_as_string()))
    application = create_app(settings)
    application.state.uploads_root = tmp_path / "uploads"
    with TestClient(application, base_url="http://localhost:8000") as client:
        yield client


def headers(api):
    return {"Origin": ORIGIN, "X-CSRF-Token": api.get("/api/accounts/session").json()["csrf_token"]}


@pytest.fixture
def signed(api, password):
    data = dict(email="upload@example.com", nickname="자료사용자", password=password)
    assert api.post("/api/accounts/signup", json=data, headers=headers(api)).status_code == 201
    response = api.post("/api/accounts/login", json={"email": data["email"], "password": password}, headers=headers(api))
    assert response.status_code == 200
    return api


def image_bytes(kind="PNG"):
    data = io.BytesIO()
    Image.new("RGB", (2, 2), "blue").save(data, format=kind)
    return data.getvalue()


def box(kind, data):
    return struct.pack(">I4s", len(data) + 8, kind) + data


def mp4_container():
    # A structural ISO-BMFF fixture, not a codec/replay test video.
    return (box(b"ftyp", b"isom\0\0\0\0isommp42") +
            box(b"moov", box(b"trak", box(b"mdia", box(b"hdlr", b"\0" * 8 + b"vide" + b"\0" * 12)))) +
            box(b"mdat", b"sample"))


def upload(api, *, name="capture.png", content=None, mime="image/png", data=None, extra_headers=None):
    return api.post("/api/materials", data=data if data is not None else {"title": "  오늘  공부  ", "memo": "복습"},
                    files={"file": (name, image_bytes() if content is None else content, mime)},
                    headers=headers(api) | (extra_headers or {}))


def stored_files(api):
    root = api.app.state.uploads_root
    return [path for path in root.rglob("*") if path.is_file()]


def count(db_session):
    db_session.expire_all()
    return db_session.scalar(select(func.count()).select_from(Material))


@pytest.mark.parametrize("name,content,mime", [
    ("C:\\fakepath\\capture.PNG", image_bytes(), "text/plain"),
    ("photo.JPEG", image_bytes("JPEG"), "image/jpeg"),
    ("lesson.mp4", mp4_container(), "video/mp4"),
], ids=["png", "jpeg", "mp4-container"])
def test_upload_persists_original_bytes_and_safe_metadata(signed, db_session, name, content, mime):
    response = upload(signed, name=name, content=content, mime=mime)
    assert response.status_code == 201
    result = response.json()
    assert result["title"] == "오늘  공부" and result["memo"] == "복습"
    assert result["size_bytes"] == len(content)
    assert set(result) == {"id", "title", "memo", "original_filename", "media_type", "mime_type", "size_bytes", "created_at", "analysis"}
    assert "\\" not in result["original_filename"]
    assert result["created_at"].endswith("Z")
    assert response.headers["cache-control"] == "private, no-store"
    material = db_session.get(Material, result["id"])
    assert material.owner_id == signed.get("/api/accounts/me").json()["id"]
    files = stored_files(signed)
    assert len(files) == 1 and files[0].read_bytes() == content
    assert files[0].name == material.stored_filename
    assert str(signed.app.state.uploads_root) not in response.text


def test_same_original_name_never_overwrites_and_empty_memo_is_optional(signed, db_session):
    first = upload(signed, data={"title": "😀" * 100, "memo": ""})
    second = upload(signed, data={"title": "가"})
    assert first.status_code == second.status_code == 201
    assert first.json()["memo"] is None
    assert len(stored_files(signed)) == count(db_session) == 2


@pytest.mark.parametrize("data", [{"title": ""}, {"title": " \t\n"}, {"title": "가" * 101},
                                      {"title": "정상", "memo": "가" * 1001}, {"title": "정상", "owner_id": "9999"}])
def test_invalid_input_and_owner_spoof_are_rejected_without_files(signed, db_session, data):
    assert upload(signed, data=data).status_code == 422
    assert not stored_files(signed) and count(db_session) == 0


@pytest.mark.parametrize("name,content,status", [
    ("empty.png", b"", 422), ("notes.txt", b"plain", 415),
    ("fake.png", b"plain text", 415), ("fake.jpg", image_bytes(), 415),
    ("broken.png", image_bytes()[:25], 415),
    ("fake.mp4", b"mp4", 415), ("header.mp4", box(b"ftyp", b"isom\0\0\0\0"), 415),
    ("audio.mp4", mp4_container().replace(b"vide", b"soun"), 415),
    ("big.png", b"x" * (storage.IMAGE_LIMIT + 1), 413),
    ("big.mp4", b"x" * (storage.VIDEO_LIMIT + 1), 413),
], ids=["empty", "text", "fake-png", "wrong-extension", "broken-image", "fake-mp4", "header-only", "audio", "image-over-limit", "video-over-limit"])
def test_invalid_file_content_or_size_is_rejected_and_cleaned(signed, db_session, name, content, status):
    assert upload(signed, name=name, content=content).status_code == status
    assert not stored_files(signed) and count(db_session) == 0


@pytest.mark.parametrize("file_fields", [["file", "file"], ["file", "other"], ["file", "other", "third"], []])
def test_requires_exactly_one_file_and_correct_field(signed, file_fields):
    response = signed.post("/api/materials", data={"title": "자료"}, headers=headers(signed),
                           files=[(key, ("a.png", image_bytes(), "image/png")) for key in file_fields])
    assert response.status_code in (415, 422)
    assert not stored_files(signed)


def test_duplicate_title_is_rejected(signed):
    response = signed.post("/api/materials", headers=headers(signed), files=[
        ("title", (None, "first")), ("title", (None, "second")),
        ("file", ("a.png", image_bytes(), "image/png")),
    ])
    assert response.status_code == 422
    assert not stored_files(signed)


def test_anonymous_and_csrf_are_required(api, signed):
    api.cookies.clear()
    assert upload(api).status_code == 401


@pytest.mark.parametrize("change", [{"X-CSRF-Token": "bad"}, {"Origin": "https://untrusted.example"}])
def test_csrf_or_origin_rejection_never_creates_files(signed, change):
    assert upload(signed, extra_headers=change).status_code == 403
    assert not stored_files(signed)


@pytest.mark.parametrize("operation", ["promote", "commit", "directory"])
def test_storage_and_commit_failure_roll_back_rows_and_files(signed, db_session, monkeypatch, operation):
    def fail(*args, **kwargs):
        if operation == "commit":
            raise OperationalError(None, None, Exception("PRIVATE connection details"))
        raise OSError("PRIVATE disk details")
    if operation == "promote":
        monkeypatch.setattr(storage, "promote_file", fail)
    elif operation == "directory":
        monkeypatch.setattr(storage, "safe_directory", fail)
    else:
        monkeypatch.setattr(Session, "commit", fail)
    response = upload(signed)
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert not stored_files(signed) and count(db_session) == 0


def test_body_limit_counts_actual_bytes_even_with_false_content_length(signed, monkeypatch):
    monkeypatch.setattr(material_router, "MAX_BODY_BYTES", 4096)
    response = upload(signed, content=b"x" * 5000, extra_headers={"Content-Length": "1"})
    assert response.status_code == 413
    assert not stored_files(signed)


def test_request_receive_timeout_cleans_up(signed, monkeypatch):
    original = material_router.Request.form

    async def slow_form(request, **kwargs):
        await asyncio.sleep(0.01)
        return await original(request, **kwargs)

    monkeypatch.setattr(material_router.Request, "form", slow_form)
    monkeypatch.setattr(material_router, "UPLOAD_RECEIVE_SECONDS", 0)
    response = upload(signed)
    assert response.status_code == 408
    assert not stored_files(signed)


@pytest.mark.parametrize("error_type", [OSError, asyncio.CancelledError])
def test_read_failure_or_cancellation_cleans_staging(signed, db_session, error_type):
    class BrokenStream(io.BytesIO):
        calls = 0

        def read(self, size):
            self.calls += 1
            if self.calls > 1:
                raise error_type()
            return b"first chunk"

    owner_id = signed.get("/api/accounts/me").json()["id"]
    file = UploadFile(filename="a.png", file=BrokenStream())
    expected = HTTPException if error_type is OSError else asyncio.CancelledError
    with pytest.raises(expected):
        create_material(db_session, owner_id, MaterialInput(title="자료"), file, signed.app.state.uploads_root)
    assert not stored_files(signed) and count(db_session) == 0


def test_storage_refuses_owner_symlink(signed, tmp_path):
    owner_id = signed.get("/api/accounts/me").json()["id"]
    root = signed.app.state.uploads_root
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / str(owner_id)).symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires Windows developer mode or privilege")
    assert upload(signed).status_code == 503
    assert not list(outside.iterdir())


def test_no_public_upload_static_route_is_added(signed):
    response = upload(signed)
    assert response.status_code == 201
    assert signed.get("/uploads/" + response.json()["original_filename"]).status_code == 404


@pytest.mark.parametrize("kind", ["png", "mp4"])
def test_exact_byte_limits_accept_valid_formats(signed, kind):
    if kind == "png":
        content = image_bytes()
        content += b"\0" * (storage.IMAGE_LIMIT - len(content))
    else:
        prefix = mp4_container().split(box(b"mdat", b"sample"))[0]
        content = prefix + box(b"mdat", b"\0" * (storage.VIDEO_LIMIT - len(prefix) - 8))
    response = upload(signed, name="limit." + kind, content=content)
    assert response.status_code == 201
    assert response.json()["size_bytes"] == len(content)


def test_each_logged_in_user_becomes_the_owner(signed, password, db_session):
    first = upload(signed)
    owner_one = signed.get("/api/accounts/me").json()["id"]
    other = {"email": "other@example.com", "nickname": "다른자료주인", "password": password}
    assert signed.post("/api/accounts/signup", json=other, headers=headers(signed)).status_code == 201
    assert signed.post("/api/accounts/login", json={"email": other["email"], "password": password}, headers=headers(signed)).status_code == 200
    second = upload(signed)
    owner_two = signed.get("/api/accounts/me").json()["id"]
    assert owner_one != owner_two
    assert db_session.get(Material, first.json()["id"]).owner_id == owner_one
    assert db_session.get(Material, second.json()["id"]).owner_id == owner_two


def test_cancellation_before_commit_rolls_back_promoted_file(signed, db_session, monkeypatch):
    owner_id = signed.get("/api/accounts/me").json()["id"]

    def cancel():
        raise asyncio.CancelledError()

    monkeypatch.setattr(db_session, "commit", cancel)
    file = UploadFile(filename="a.png", file=io.BytesIO(image_bytes()))
    with pytest.raises(asyncio.CancelledError):
        create_material(db_session, owner_id, MaterialInput(title="자료"), file, signed.app.state.uploads_root)
    assert not stored_files(signed) and count(db_session) == 0


def test_disconnect_during_multipart_parsing_closes_temporary_files(signed, db_session, monkeypatch):
    from starlette import formparsers
    original = formparsers.SpooledTemporaryFile
    handles = []

    def track_file(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", track_file)
    messages = iter([
        {"type": "http.request", "more_body": True, "body":
         b'--abc\r\nContent-Disposition: form-data; name="file"; filename="a.png"\r\n\r\nfirst-chunk'},
        {"type": "http.disconnect"},
    ])

    async def receive():
        return next(messages)

    request = Request({"type": "http", "method": "POST", "path": "/api/materials", "app": signed.app,
                       "headers": [(b"content-type", b"multipart/form-data; boundary=abc")]}, receive=receive)
    from types import SimpleNamespace
    from fastapi import Response
    with pytest.raises(HTTPException) as error:
        asyncio.run(material_router.upload_material(request, Response(), SimpleNamespace(id=1), db_session, None))
    assert error.value.status_code == 400
    assert handles and all(handle.closed for handle in handles)
    assert not stored_files(signed) and count(db_session) == 0


def test_partial_disk_write_failure_removes_temporary_file(signed, db_session, monkeypatch):
    original = storage.os.fdopen

    class FailingWriter:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, data):
            self.stream.write(data[:10])
            raise OSError("PRIVATE disk full")

    monkeypatch.setattr(storage.os, "fdopen", lambda *a, **kw: FailingWriter(original(*a, **kw)))
    response = upload(signed)
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert not stored_files(signed) and count(db_session) == 0


def test_symlink_detection_rejects_owner_directory_without_os_privileges(signed, db_session, monkeypatch):
    from pathlib import Path
    owner_id = signed.get("/api/accounts/me").json()["id"]
    unsafe = signed.app.state.uploads_root / str(owner_id)
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == unsafe or original(path))
    assert upload(signed).status_code == 503
    assert not stored_files(signed) and count(db_session) == 0
