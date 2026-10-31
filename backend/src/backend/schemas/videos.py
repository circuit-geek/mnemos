import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.models import JobStatus, VideoStatus


class VideoAcceptedResponse(BaseModel):
    video_id: uuid.UUID
    job_id: uuid.UUID
    status: VideoStatus


class ProcessingJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    duration_seconds: float | None = None
    status: VideoStatus
    requested_concepts: list[str] | None = None
    tracked_concepts: list[str] | None = None
    created_at: datetime
    processing_job: ProcessingJobRead | None = None


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tracked_object_id: uuid.UUID | None = None
    timestamp_seconds: float
    frame_number: int | None = None
    label: str | None = None
    confidence: float | None = None
    bbox: list[int] | None = None
    mask_reference: str | None = None
    attributes: dict[str, Any]
