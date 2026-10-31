import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.models.types import JSONType
from backend.models.video import utcnow


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )
    tracked_object_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tracked_objects.id", ondelete="CASCADE"), index=True
    )
    timestamp_seconds: Mapped[float] = mapped_column(Float, index=True)
    frame_number: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[float | None] = mapped_column(Float)
    # Pixel half-open [left, top, right, bottom], as emitted by the SAM experiment.
    bbox: Mapped[list[int] | None] = mapped_column(JSONType)
    mask_reference: Mapped[str | None] = mapped_column(String(512))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
