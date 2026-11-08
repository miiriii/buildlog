from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.accounts.validation import normalize_email, validate_nickname
from app.core.security import hash_password


def create_user(session: Session, *, email: str, nickname: str, password: str) -> User:
    user = User(
        email=normalize_email(email),
        nickname=validate_nickname(nickname),
        password_hash=hash_password(password),
        is_admin=False,
    )
    session.add(user)
    session.flush()
    # The caller owns commit/rollback so future API requests can remain atomic.
    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == normalize_email(email)))
