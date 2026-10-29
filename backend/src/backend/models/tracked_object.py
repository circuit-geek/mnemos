import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.models.types import JSONType
from backend.models.video import utcnow


class TrackedObject(Base):
    __tablename__ = "tracked_objects"
    # SAM tracking IDs are only meaningful within one video.
    __table_args__ = (UniqueConstraint("video_id", "external_tracking_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )
    external_tracking_id: Mapped[str] = mapped_column(String(64))
    label: Mapped[str | None] = mapped_column(String(255))
    first_seen_at: Mapped[float | None] = mapped_column(Float)
    last_seen_at: Mapped[float | None] = mapped_column(Float)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
