import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.db.session import get_session

DatabaseSession = Annotated[Session, Depends(get_session)]


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not isinstance(token, str) or not token.isascii() or len(token) < 32:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def require_csrf(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin not in request.app.state.settings.cors_origins:
        raise HTTPException(403, "허용되지 않은 요청입니다.")
    supplied = request.headers.get("x-csrf-token", "")
    expected = request.session.get("csrf_token")
    if (not supplied.isascii() or not isinstance(expected, str)
            or not expected.isascii() or not secrets.compare_digest(supplied, expected)):
        raise HTTPException(403, "요청 확인이 만료되었습니다. 다시 시도해 주세요.")


def optional_user(request: Request, session: DatabaseSession) -> User | None:
    user_id = request.session.get("user_id")
    if type(user_id) is not int or user_id <= 0:
        request.session.pop("user_id", None)
        return None
    user = session.get(User, user_id)
    if user is None:
        request.session.pop("user_id", None)
    return user


def current_user(user: Annotated[User | None, Depends(optional_user)]) -> User:
    if user is None:
        raise HTTPException(401, "로그인이 필요합니다.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
