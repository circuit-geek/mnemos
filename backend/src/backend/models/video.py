import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.models.enums import VideoStatus
from backend.models.types import JSONType, string_enum


def utcnow() -> datetime:
    return datetime.now(UTC)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    storage_key: Mapped[str] = mapped_column(String(512))
    status: Mapped[VideoStatus] = mapped_column(
        string_enum(VideoStatus), default=VideoStatus.UPLOADED, index=True
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    # What the uploader asked to track (None = let the model discover it) and what was tracked.
    requested_concepts: Mapped[list[str] | None] = mapped_column(JSONType)
    tracked_concepts: Mapped[list[str] | None] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
