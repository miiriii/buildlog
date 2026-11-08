from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from app.accounts.validation import normalize_email, validate_nickname


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class LoginInput(InputModel):
    email: str
    password: SecretStr

    @field_validator("email", mode="before")
    @classmethod
    def check_email(cls, value):
        return normalize_email(value)

    @field_validator("password", mode="before")
    @classmethod
    def check_password(cls, value):
        if not isinstance(value, str) or not 8 <= len(value) <= 64:
            raise ValueError("Password must contain 8 to 64 characters")
        return value


class SignupInput(LoginInput):
    nickname: str

    @field_validator("nickname", mode="before")
    @classmethod
    def check_nickname(cls, value):
        return validate_nickname(value)


class NicknameInput(InputModel):
    nickname: str

    @field_validator("nickname", mode="before")
    @classmethod
    def check_nickname(cls, value):
        return validate_nickname(value)


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    nickname: str


class SessionOutput(BaseModel):
    user: UserOutput | None
    csrf_token: str


class MessageOutput(BaseModel):
    message: str
