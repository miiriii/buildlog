import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.accounts.dependencies import (
    CurrentUser, DatabaseSession, ensure_csrf_token, optional_user, require_csrf,
)
from app.accounts.models import User
from app.accounts.schemas import LoginInput, MessageOutput, NicknameInput, SessionOutput, SignupInput, UserOutput
from app.accounts.services import create_user, get_user_by_email
from app.core.security import hash_password, verify_password

router = APIRouter(prefix="/api/accounts", tags=["accounts"])
_dummy_hash = hash_password(secrets.token_urlsafe(32))
_write_dependencies = [Depends(require_csrf)]


@router.get("/session", response_model=SessionOutput)
def read_session(request: Request, response: Response,
                 user: Annotated[User | None, Depends(optional_user)]):
    response.headers["Cache-Control"] = "no-store"
    return SessionOutput(
        user=UserOutput.model_validate(user) if user else None,
        csrf_token=ensure_csrf_token(request),
    )


@router.post("/signup", response_model=MessageOutput, status_code=201, dependencies=_write_dependencies)
def signup(data: SignupInput, session: DatabaseSession):
    if get_user_by_email(session, data.email):
        raise HTTPException(409, "이미 사용 중인 이메일입니다.")
    if session.scalar(select(User.id).where(User.nickname == data.nickname)):
        raise HTTPException(409, "이미 사용 중인 닉네임입니다.")
    try:
        create_user(session, email=data.email, nickname=data.nickname,
                    password=data.password.get_secret_value())
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "이미 사용 중인 이메일 또는 닉네임입니다.") from None
    return MessageOutput(message="회원가입을 마쳤습니다. 로그인해 주세요.")


@router.post("/login", response_model=SessionOutput, dependencies=_write_dependencies)
def login(data: LoginInput, request: Request, response: Response, session: DatabaseSession):
    user = get_user_by_email(session, data.email)
    valid = verify_password(data.password.get_secret_value(), user.password_hash if user else _dummy_hash)
    if not valid or user is None:
        raise HTTPException(401, "이메일 또는 비밀번호가 맞지 않습니다.")
    request.session.clear()
    request.session["user_id"] = user.id
    response.headers["Cache-Control"] = "no-store"
    return SessionOutput(user=UserOutput.model_validate(user), csrf_token=ensure_csrf_token(request))


@router.get("/me", response_model=UserOutput)
def read_me(user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.patch("/me", response_model=UserOutput, dependencies=_write_dependencies)
def change_nickname(data: NicknameInput, user: CurrentUser, session: DatabaseSession):
    other = session.scalar(select(User.id).where(User.nickname == data.nickname, User.id != user.id))
    if other:
        raise HTTPException(409, "이미 사용 중인 닉네임입니다.")
    user.nickname = data.nickname
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "이미 사용 중인 닉네임입니다.") from None
    return user
