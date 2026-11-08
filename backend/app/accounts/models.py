from sqlalchemy import Boolean, CheckConstraint, Integer, String, UniqueConstraint, event, false
from sqlalchemy.orm import Mapped, Session, mapped_column, validates

from app.accounts.validation import normalize_email, validate_nickname
from app.core.security import validate_password_hash
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email"),
        UniqueConstraint("nickname"),
        CheckConstraint("length(email) BETWEEN 3 AND 320", name="email_length"),
        CheckConstraint("email = trim(email)", name="email_trimmed"),
        CheckConstraint("length(nickname) BETWEEN 2 AND 20", name="nickname_length"),
        CheckConstraint("nickname = trim(nickname)", name="nickname_trimmed"),
        CheckConstraint("password_hash LIKE '$argon2id$%'", name="password_hash_format"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    nickname: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

    @validates("email")
    def check_email(self, _key, value):
        return normalize_email(value)

    @validates("nickname")
    def check_nickname(self, _key, value):
        return validate_nickname(value)

    @validates("password_hash")
    def check_password_hash(self, _key, value):
        return validate_password_hash(value)

    def __repr__(self) -> str:
        return f"User(id={self.id!r})"


@event.listens_for(Session, "before_flush")
def validate_users(session, _flush_context, _instances):
    for user in session.new.union(session.dirty):
        if isinstance(user, User) and user not in session.deleted:
            # Also catches omitted fields and invalid values before any SQL is sent.
            user.email = normalize_email(user.email)
            user.nickname = validate_nickname(user.nickname)
            user.password_hash = validate_password_hash(user.password_hash)
