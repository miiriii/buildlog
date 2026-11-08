"""Private read/delete endpoints; isolated DB and files from upload fixtures."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.materials import storage
from app.materials.models import Material
from test_materials_upload import api, signed, headers, upload, image_bytes, mp4_container, stored_files, count


def create(signed, **kwargs):
    response = upload(signed, **kwargs)
    assert response.status_code == 201
    return response.json()["id"]


def original(material_id):
    return f"/api/materials/{material_id}/file"


def test_empty_and_latest_ordered_list_returns_only_safe_metadata(signed, db_session):
    response = signed.get("/api/materials")
    assert response.json() == {"items": []}
    assert response.headers["cache-control"] == "private, no-store"
    first, second, third = [create(signed) for _ in range(3)]
    common = datetime(2026, 10, 20, tzinfo=UTC)
    db_session.execute(update(Material).values(created_at=common))
    db_session.commit()
    response = signed.get("/api/materials")
    items = response.json()["items"]
    assert [item["id"] for item in items] == [third, second, first]
    assert all(item["created_at"].endswith("Z") for item in items)
    assert all("stored_filename" not in item and "owner_id" not in item for item in items)
    assert str(signed.app.state.uploads_root) not in response.text
    db_session.execute(update(Material).where(Material.id == first).values(created_at=datetime(2026, 11, 1, tzinfo=UTC)))
    db_session.commit()
    assert [item["id"] for item in signed.get("/api/materials").json()["items"]] == [first, third, second]


def test_original_bytes_mime_unicode_filename_and_private_headers(signed):
    material_id = create(signed, name='복습 "캡처".png')
    response = signed.get(original(material_id))
    assert response.status_code == 200 and response.content == image_bytes()
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"].startswith("inline; filename*=utf-8''")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["accept-ranges"] == "bytes"


@pytest.mark.parametrize("range_header,expected_slice", [
    ("bytes=0-7", slice(0, 8)), ("bytes=8-", slice(8, None)), ("bytes=-5", slice(-5, None)),
])
def test_mp4_byte_range_returns_authorized_original_slice(signed, range_header, expected_slice):
    data = mp4_container()
    material_id = create(signed, name="video.mp4", content=data, mime="video/mp4")
    response = signed.get(original(material_id), headers={"Range": range_header})
    assert response.status_code == 206
    assert response.content == data[expected_slice]
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["content-range"].startswith("bytes ")
    assert response.headers["cache-control"] == "private, no-store"


def test_multiple_ranges_and_if_range(signed):
    material_id = create(signed)
    response = signed.get(original(material_id), headers={"Range": "bytes=0-2,10-12"})
    assert response.status_code == 206
    assert response.headers["content-type"].startswith("multipart/byteranges")
    assert b"Content-Range: bytes 0-2/" in response.content or b"content-range: bytes 0-2/" in response.content.lower()
    full = signed.get(original(material_id))
    partial = signed.get(original(material_id), headers={"Range": "bytes=0-2", "If-Range": full.headers["etag"]})
    assert partial.status_code == 206
    fallback = signed.get(original(material_id), headers={"Range": "bytes=0-2", "If-Range": '"old"'})
    assert fallback.status_code == 200 and fallback.content == full.content


@pytest.mark.parametrize("range_header,status", [("bytes=999999-", 416), ("broken", 400)])
def test_invalid_ranges_have_private_headers(signed, range_header, status):
    material_id = create(signed)
    response = signed.get(original(material_id), headers={"Range": range_header})
    assert response.status_code == status
    assert response.headers["cache-control"] == "private, no-store"
    assert str(signed.app.state.uploads_root) not in response.text
    # A later deletion succeeds, so the early range-error response closed the handle.
    assert signed.delete(f"/api/materials/{material_id}", headers=headers(signed)).status_code == 204


def test_other_user_including_admin_cannot_list_read_range_or_delete(signed, db_session, password):
    material_id = create(signed)
    user = {"email": "other@example.com", "nickname": "다른사용자", "password": password}
    assert signed.post("/api/accounts/signup", json=user, headers=headers(signed)).status_code == 201
    assert signed.post("/api/accounts/login", json={"email": user["email"], "password": password}, headers=headers(signed)).status_code == 200
    # Admin status must not bypass materials ownership.
    from app.accounts.models import User
    second_id = signed.get("/api/accounts/me").json()["id"]
    db_session.execute(update(User).where(User.id == second_id).values(is_admin=True))
    db_session.commit()
    assert signed.get("/api/materials").json() == {"items": []}
    for response in [signed.get(original(material_id)), signed.get(original(material_id), headers={"Range": "bytes=0-1"}),
                     signed.delete(f"/api/materials/{material_id}", headers=headers(signed))]:
        assert response.status_code == 404
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json() == signed.get(original(999999)).json()
    assert count(db_session) == 1 and len(stored_files(signed)) == 1


@pytest.mark.parametrize("method,path,request_headers", [
    ("GET", "/api/materials", {}), ("GET", "/api/materials/1/file", {}),
    ("GET", "/api/materials/1/file", {"Range": "bytes=0-1"}),
    ("DELETE", "/api/materials/1", {}),
])
def test_anonymous_access_is_denied(api, method, path, request_headers):
    response = api.request(method, path, headers=request_headers)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "private, no-store"


def test_delete_removes_file_and_row_and_repeat_returns_404(signed, db_session):
    material_id = create(signed)
    response = signed.delete(f"/api/materials/{material_id}", headers=headers(signed))
    assert response.status_code == 204 and response.content == b""
    assert response.headers["cache-control"] == "private, no-store"
    assert count(db_session) == 0 and not stored_files(signed)
    assert signed.get("/api/materials").json() == {"items": []}
    assert signed.get(original(material_id)).status_code == 404
    assert signed.delete(f"/api/materials/{material_id}", headers=headers(signed)).status_code == 404


@pytest.mark.parametrize("bad_headers", [{"X-CSRF-Token": "wrong"}, {"Origin": "https://other.example"}])
def test_delete_requires_csrf_and_origin(signed, db_session, bad_headers):
    material_id = create(signed)
    response = signed.delete(f"/api/materials/{material_id}", headers=headers(signed) | bad_headers)
    assert response.status_code == 403
    assert count(db_session) == 1 and len(stored_files(signed)) == 1


def test_missing_file_returns_404_but_owner_can_remove_metadata(signed, db_session):
    material_id = create(signed)
    stored_files(signed)[0].unlink()
    assert signed.get(original(material_id)).status_code == 404
    assert signed.delete(f"/api/materials/{material_id}", headers=headers(signed)).status_code == 204
    assert count(db_session) == 0


@pytest.mark.parametrize("failure", ["move", "commit"])
def test_failed_deletion_preserves_original_and_row(signed, db_session, monkeypatch, failure):
    material_id = create(signed)
    path = stored_files(signed)[0]
    expected = path.read_bytes()

    def fail(*args, **kwargs):
        if failure == "commit":
            raise OperationalError(None, None, Exception("PRIVATE connection information"))
        raise OSError("PRIVATE filesystem information")

    monkeypatch.setattr(Session, "commit", fail) if failure == "commit" else monkeypatch.setattr(storage, "quarantine_file", fail)
    response = signed.delete(f"/api/materials/{material_id}", headers=headers(signed))
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert count(db_session) == 1 and path.read_bytes() == expected
    assert len(stored_files(signed)) == 1
    assert signed.get(original(material_id)).content == expected


def test_failed_purge_after_commit_is_internal_cleanup_not_failed_deletion(signed, db_session, monkeypatch, caplog):
    from pathlib import Path
    material_id = create(signed)
    original_unlink = Path.unlink

    def fail_trash(path, *args, **kwargs):
        if path.parent.name == ".trash":
            raise OSError("PRIVATE path and disk failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_trash)
    response = signed.delete(f"/api/materials/{material_id}", headers=headers(signed))
    assert response.status_code == 204 and count(db_session) == 0
    assert signed.get(original(material_id)).status_code == 404
    files = stored_files(signed)
    assert len(files) == 1 and files[0].parent.name == ".trash"
    assert "reconciliation required" in caplog.text and "PRIVATE" not in caplog.text


def test_bad_db_storage_path_cannot_read_or_delete_outside_root(signed, db_session, tmp_path):
    material_id = create(signed)
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"do not read or delete")
    db_session.execute(update(Material).where(Material.id == material_id).values(stored_filename="../outside.png"))
    db_session.commit()
    assert signed.get(original(material_id)).status_code == 503
    assert signed.delete(f"/api/materials/{material_id}", headers=headers(signed)).status_code == 503
    assert outside.read_bytes() == b"do not read or delete"
    assert count(db_session) == 1


def test_cors_exposes_original_headers_and_accepts_range_preflight(signed):
    material_id = create(signed)
    response = signed.get(original(material_id), headers={"Origin": "http://localhost:5173", "Range": "bytes=0-2"})
    assert response.status_code == 206
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "Content-Range" in response.headers["access-control-expose-headers"]
    response = signed.options(original(material_id), headers={"Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "range,if-range"})
    assert response.status_code == 200


def test_list_database_failure_is_sanitized_and_not_cached(signed, monkeypatch):
    def fail(*args, **kwargs):
        raise OperationalError(None, None, Exception("PRIVATE DB connection details"))

    monkeypatch.setattr(Session, "scalars", fail)
    response = signed.get("/api/materials")
    assert response.status_code == 503 and "PRIVATE" not in response.text
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("link_kind", ["file", "directory"])
def test_read_and_delete_reject_detected_symlinks(signed, db_session, monkeypatch, link_kind):
    from pathlib import Path
    material_id = create(signed)
    path = stored_files(signed)[0]
    unsafe = path if link_kind == "file" else path.parent
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == unsafe or original(p))
    assert signed.get(f"/api/materials/{material_id}/file").status_code == 503
    assert signed.delete(f"/api/materials/{material_id}", headers=headers(signed)).status_code == 503
    assert path.read_bytes() == image_bytes() and count(db_session) == 1


def test_cancelled_delete_restores_file_before_propagating(signed, db_session, monkeypatch):
    import asyncio
    from app.materials.services import delete_material
    material_id = create(signed)
    owner_id = signed.get("/api/accounts/me").json()["id"]
    path = stored_files(signed)[0]

    def cancel():
        raise asyncio.CancelledError()

    monkeypatch.setattr(db_session, "commit", cancel)
    with pytest.raises(asyncio.CancelledError):
        delete_material(db_session, owner_id, material_id, signed.app.state.uploads_root)
    assert path.read_bytes() == image_bytes() and count(db_session) == 1
    assert len(stored_files(signed)) == 1


def test_restore_failure_keeps_quarantined_bytes_and_logs_no_private_details(signed, db_session, monkeypatch, caplog):
    material_id = create(signed)

    def fail_commit(*args, **kwargs):
        raise OperationalError(None, None, Exception("PRIVATE database"))

    def fail_restore(*args, **kwargs):
        raise OSError("PRIVATE filesystem")

    monkeypatch.setattr(Session, "commit", fail_commit)
    monkeypatch.setattr(storage, "restore_file", fail_restore)
    response = signed.delete(f"/api/materials/{material_id}", headers=headers(signed))
    assert response.status_code == 503 and count(db_session) == 1
    files = stored_files(signed)
    assert len(files) == 1 and files[0].parent.name == ".trash" and files[0].read_bytes() == image_bytes()
    assert "recovery failed" in caplog.text and "PRIVATE" not in caplog.text
