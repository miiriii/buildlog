import secrets
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.core.config import Settings
from app.main import create_app

ORIGIN = "http://localhost:5173"
PREFIX = "/api/accounts"


@pytest.fixture
def api(db_engine) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None, app_env="test", secret_key=SecretStr(secrets.token_urlsafe(48)),
        database_url=SecretStr(db_engine.url.render_as_string()),
    )
    with TestClient(create_app(settings), base_url="http://localhost:8000") as client:
        yield client


def write(api, method, path, values, **headers):
    token = api.get(f"{PREFIX}/session").json()["csrf_token"]
    return api.request(method, PREFIX + path, json=values,
                       headers={"Origin": ORIGIN, "X-CSRF-Token": token, **headers})


def signup(api, password, *, email="one@example.com", nickname="첫사용자"):
    return write(api, "POST", "/signup", {"email": email, "nickname": nickname, "password": password})


def login(api, password, email="one@example.com"):
    return write(api, "POST", "/login", {"email": email, "password": password})


def test_signup_does_not_log_in_and_login_returns_only_safe_user_fields(api, password):
    assert signup(api, password).status_code == 201
    assert api.get(f"{PREFIX}/session").json()["user"] is None
    response = login(api, password)
    assert response.status_code == 200
    assert set(response.json()["user"]) == {"id", "email", "nickname"}
    assert password not in response.text
    assert api.get(f"{PREFIX}/me").json()["nickname"] == "첫사용자"


def test_session_cookie_flags_and_no_cache(api):
    response = api.get(f"{PREFIX}/session")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=28800" in cookie
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("field,value", [
    ("email", "not-an-email"), ("email", ""),
    ("nickname", "가"), ("nickname", "가" * 21), ("nickname", "잘 못"),
    ("nickname", "no!"), ("nickname", "   "),
])
def test_signup_input_conditions(api, password, field, value):
    values = {"email": "one@example.com", "nickname": "학습자", "password": password}
    values[field] = value
    response = write(api, "POST", "/signup", values)
    assert response.status_code == 422
    assert password not in response.text
    assert api.get(f"{PREFIX}/session").json()["user"] is None


@pytest.mark.parametrize("length,expected", [(7, 422), (8, 201), (64, 201), (65, 422)])
def test_signup_password_boundaries(api, length, expected):
    password = secrets.token_hex(40)[:length]
    response = signup(api, password)
    assert response.status_code == expected
    assert password not in response.text


@pytest.mark.parametrize("nickname", ["가나", "가" * 20])
def test_signup_nickname_boundaries_and_trim(api, password, nickname):
    assert signup(api, password, email=" One@Example.COM ", nickname=f" {nickname} ").status_code == 201
    assert login(api, password).json()["user"]["nickname"] == nickname


@pytest.mark.parametrize("field", ["email", "nickname"])
def test_signup_duplicates_are_rejected_without_changing_original(api, password, field):
    assert signup(api, password).status_code == 201
    values = {"email": "two@example.com", "nickname": "두번째", "password": password}
    values[field] = "one@example.com" if field == "email" else "첫사용자"
    response = write(api, "POST", "/signup", values)
    assert response.status_code == 409
    assert login(api, password).json()["user"]["nickname"] == "첫사용자"


def test_cannot_set_admin_through_signup(api, password, db_session):
    response = write(api, "POST", "/signup", {
        "email": "one@example.com", "nickname": "학습자", "password": password, "is_admin": True,
    })
    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(User)) == 0


def test_incorrect_and_unknown_login_return_same_message(api, password):
    assert signup(api, password).status_code == 201
    wrong = login(api, secrets.token_urlsafe(24))
    unknown = login(api, password, email="unknown@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert api.get(f"{PREFIX}/me").status_code == 401


def test_password_spaces_are_preserved(api, password):
    spaced = f" {password} "
    assert signup(api, spaced).status_code == 201
    assert login(api, password).status_code == 401
    assert login(api, spaced).status_code == 200


def test_anonymous_user_cannot_access_or_change_account(api):
    assert api.get(f"{PREFIX}/me").status_code == 401
    assert write(api, "PATCH", "/me", {"nickname": "변경시도"}).status_code == 401


@pytest.mark.parametrize("method,path,values", [
    ("POST", "/signup", {"email": "one@example.com", "nickname": "학습자"}),
    ("POST", "/login", {"email": "one@example.com"}),
    ("PATCH", "/me", {"nickname": "변경시도"}),
])
def test_all_writes_require_correct_origin_and_csrf(api, password, method, path, values):
    values = {**values, **({"password": password} if method == "POST" else {})}
    token = api.get(f"{PREFIX}/session").json()["csrf_token"]
    for headers in (
        {}, {"Origin": ORIGIN}, {"Origin": "https://unapproved.example", "X-CSRF-Token": token},
        {"Origin": ORIGIN, "X-CSRF-Token": secrets.token_urlsafe(32)},
    ):
        assert api.request(method, PREFIX + path, json=values, headers=headers).status_code == 403


def test_login_rotates_csrf_token(api, password):
    assert signup(api, password).status_code == 201
    before = api.get(f"{PREFIX}/session").json()["csrf_token"]
    response = login(api, password)
    assert response.json()["csrf_token"] != before
    rejected = api.patch(f"{PREFIX}/me", json={"nickname": "새닉네임"},
                         headers={"Origin": ORIGIN, "X-CSRF-Token": before})
    assert rejected.status_code == 403


def test_changed_nickname_is_read_from_db_and_survives_new_session_read(api, password):
    assert signup(api, password).status_code == 201
    assert login(api, password).status_code == 200
    response = write(api, "PATCH", "/me", {"nickname": " 새닉네임 "})
    assert response.status_code == 200
    assert response.json()["nickname"] == "새닉네임"
    assert api.get(f"{PREFIX}/session").json()["user"]["nickname"] == "새닉네임"
    assert api.get(f"{PREFIX}/me").json()["nickname"] == "새닉네임"


@pytest.mark.parametrize("nickname", ["가", "가" * 21, "   ", "나!", "두 글자"])
def test_invalid_nickname_update_preserves_saved_value(api, password, nickname):
    signup(api, password)
    login(api, password)
    assert write(api, "PATCH", "/me", {"nickname": nickname}).status_code == 422
    assert api.get(f"{PREFIX}/me").json()["nickname"] == "첫사용자"


def test_duplicate_nickname_and_target_id_cannot_modify_other_account(api, password, db_engine):
    signup(api, password)
    signup(api, password, email="two@example.com", nickname="다른사람")
    login(api, password)
    assert write(api, "PATCH", "/me", {"nickname": "다른사람"}).status_code == 409
    assert write(api, "PATCH", "/me", {"nickname": "변경시도", "id": 2}).status_code == 422
    assert write(api, "PATCH", "/me", {"nickname": "변경시도", "user_id": 2}).status_code == 422
    with Session(db_engine) as session:
        assert session.scalar(select(User).where(User.email == "two@example.com")).nickname == "다른사람"
    assert api.get(f"{PREFIX}/me").json()["nickname"] == "첫사용자"
    assert write(api, "PATCH", "/me", {"nickname": "첫사용자"}).status_code == 200


def test_modified_or_expired_cookie_does_not_authenticate(api, password, monkeypatch):
    from itsdangerous import TimestampSigner

    signup(api, password)
    login(api, password)
    signed_cookie = api.cookies.get("buildlog_session")
    tampered = api.get(f"{PREFIX}/me", headers={"Cookie": f"buildlog_session={signed_cookie}invalid"})
    assert tampered.status_code == 401
    original = TimestampSigner.get_timestamp
    future = original(TimestampSigner(secrets.token_urlsafe(32))) + 28801
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: future)
    expired = api.get(f"{PREFIX}/me", headers={"Cookie": f"buildlog_session={signed_cookie}"})
    assert expired.status_code == 401


def test_storage_failure_returns_safe_message(api, password, monkeypatch):
    import app.accounts.router as routes

    def unavailable(*args, **kwargs):
        raise OperationalError("unavailable", {}, Exception())
    monkeypatch.setattr(routes, "create_user", unavailable)
    response = signup(api, password)
    assert response.status_code == 503
    assert password not in response.text
    assert "SELECT" not in response.text


def test_deleted_user_no_longer_authenticates(api, password, db_engine):
    signup(api, password)
    login(api, password)
    with Session(db_engine) as session, session.begin():
        user = session.scalar(select(User))
        session.delete(user)
    assert api.get(f"{PREFIX}/me").status_code == 401
    assert api.get(f"{PREFIX}/session").json()["user"] is None


def test_secure_cookie_and_csrf_tokens_are_bound_to_each_client(db_engine):
    settings = Settings(
        _env_file=None, app_env="test", secret_key=SecretStr(secrets.token_urlsafe(48)),
        database_url=SecretStr(db_engine.url.render_as_string()), session_cookie_secure=True,
    )
    app = create_app(settings)
    with TestClient(app, base_url="https://localhost:8000") as first:
        response = first.get(f"{PREFIX}/session")
        assert "secure" in response.headers["set-cookie"].lower()
        first_token = response.json()["csrf_token"]
        with TestClient(app, base_url="https://localhost:8000") as second:
            second.get(f"{PREFIX}/session")
            result = second.patch(f"{PREFIX}/me", json={"nickname": "변경시도"},
                                  headers={"Origin": ORIGIN, "X-CSRF-Token": first_token})
            assert result.status_code == 403
