import re

from email_validator import EmailNotValidError, validate_email

_NICKNAME_PATTERN = re.compile(r"[A-Za-z0-9_\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]{2,20}")


def normalize_email(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Email is required")
    try:
        result = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError:
        raise ValueError("A valid email address is required") from None
    return result.normalized.lower()


def validate_nickname(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Nickname is required")
    value = value.strip()
    if not _NICKNAME_PATTERN.fullmatch(value):
        raise ValueError("Nickname must contain 2 to 20 Korean or English letters, digits or underscores")
    return value
