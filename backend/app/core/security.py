from argon2 import extract_parameters
from argon2.low_level import Type
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

_password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not 8 <= len(password) <= 64:
        raise ValueError("Password must contain 8 to 64 characters")
    return _password_hasher.hash(password)


def validate_password_hash(value: str) -> str:
    try:
        parameters = extract_parameters(value)
        if parameters.type != Type.ID:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError("An Argon2id password hash is required") from None
    return value


def verify_password(password: str, password_hash: str) -> bool:
    if not isinstance(password, str) or not 8 <= len(password) <= 64:
        return False
    try:
        return _password_hasher.verify(password, password_hash)
    except (UnknownHashError, ValueError, TypeError):
        return False
