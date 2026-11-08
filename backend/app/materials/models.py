from datetime import UTC, datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint("stored_filename"),
        CheckConstraint("length(title) BETWEEN 1 AND 100", name="title_length"),
        CheckConstraint("title = trim(title)", name="title_trimmed"),
        CheckConstraint("memo IS NULL OR length(memo) BETWEEN 1 AND 1000", name="memo_length"),
        CheckConstraint("length(original_filename) > 0", name="original_filename_length"),
        CheckConstraint("length(stored_filename) BETWEEN 1 AND 255", name="stored_filename_length"),
        CheckConstraint("media_type IN ('image', 'video')", name="media_type"),
        CheckConstraint("mime_type IN ('image/png', 'image/jpeg', 'video/mp4')", name="mime_type"),
        CheckConstraint(
            "(media_type = 'image' AND mime_type IN ('image/png', 'image/jpeg') "
            "AND size_bytes BETWEEN 1 AND 5242880) OR "
            "(media_type = 'video' AND mime_type = 'video/mp4' "
            "AND size_bytes BETWEEN 1 AND 31457280)", name="type_size",
        ),
        Index("ix_materials_owner_created_id", "owner_id", "created_at", "id"),
        CheckConstraint("analysis_status IN ('not_requested','pending','processing','succeeded','failed')", name="analysis_status"),
        CheckConstraint("analysis_attempt_count BETWEEN 0 AND 3 AND analysis_version >= 0", name="analysis_counts"),
        CheckConstraint("(analysis_input_tokens IS NULL OR analysis_input_tokens >= 0) AND (analysis_output_tokens IS NULL OR analysis_output_tokens >= 0)", name="analysis_usage"),
        CheckConstraint("(analysis_status = 'succeeded' AND length(trim(analysis_summary)) BETWEEN 1 AND 2000 AND analysis_summary IS NOT NULL AND analysis_error_code IS NULL AND analysis_completed_at IS NOT NULL) OR (analysis_status != 'succeeded' AND analysis_summary IS NULL)", name="analysis_summary"),
        CheckConstraint("analysis_status != 'failed' OR (analysis_error_code IS NOT NULL AND analysis_completed_at IS NOT NULL)", name="analysis_failure"),
        CheckConstraint("analysis_status != 'pending' OR (analysis_error_code IS NULL AND analysis_completed_at IS NULL)", name="analysis_pending"),
        CheckConstraint("(analysis_status = 'processing' AND analysis_job_token IS NOT NULL AND analysis_started_at IS NOT NULL AND analysis_lease_expires_at IS NOT NULL) OR (analysis_status != 'processing' AND analysis_job_token IS NULL AND analysis_lease_expires_at IS NULL)", name="analysis_lease"),
        Index("ix_materials_analysis_queue", "analysis_status", "created_at", "id"),
        Index("ix_materials_analysis_owner", "owner_id", "analysis_status"),
        Index("ix_materials_analysis_expiry", "analysis_status", "analysis_lease_expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(5), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(20), default="not_requested", server_default="not_requested", nullable=False)
    analysis_summary: Mapped[str | None] = mapped_column(Text)
    analysis_error_code: Mapped[str | None] = mapped_column(String(64))
    analysis_model: Mapped[str | None] = mapped_column(String(100))
    analysis_prompt_version: Mapped[str | None] = mapped_column(String(40))
    analysis_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_job_token: Mapped[str | None] = mapped_column(String(36))
    analysis_lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    analysis_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    analysis_input_tokens: Mapped[int | None] = mapped_column(BigInteger)
    analysis_output_tokens: Mapped[int | None] = mapped_column(BigInteger)
    analysis_metadata: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC), server_default=func.now(),
    )

    @validates("title")
    def validate_title(self, _key, value):
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
            raise ValueError("Material title must contain 1 to 100 characters")
        return value.strip()

    @validates("memo")
    def validate_memo(self, _key, value):
        if value is not None and (not isinstance(value, str) or len(value) > 1000):
            raise ValueError("Material memo must contain at most 1000 characters")
        return value if value else None

    def __repr__(self):
        return f"Material(id={self.id!r}, owner_id={self.owner_id!r})"

    @property
    def analysis(self):
        from app.materials.analysis_schemas import public_analysis
        return public_analysis(self)
