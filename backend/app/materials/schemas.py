from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
from app.materials.analysis_schemas import AnalysisOutput


class MaterialInput(BaseModel):
    title: str
    memo: str | None = None

    @field_validator("title")
    @classmethod
    def title_length(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise ValueError("Invalid title length")
        return value

    @field_validator("memo")
    @classmethod
    def memo_length(cls, value):
        if value is not None and len(value) > 1000:
            raise ValueError("Invalid memo length")
        return value or None


class MaterialOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    memo: str | None
    original_filename: str
    media_type: Literal["image", "video"]
    mime_type: str
    size_bytes: int
    created_at: datetime
    analysis: AnalysisOutput

    @field_validator("created_at")
    @classmethod
    def utc_datetime(cls, value):
        # SQLite test round-trips drop timezone info; stored defaults are UTC.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class MaterialList(BaseModel):
    items: list[MaterialOutput]
