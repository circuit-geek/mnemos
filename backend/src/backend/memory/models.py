from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class Video(MemoryModel):
    video_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    duration_ms: int | None = Field(default=None, ge=0)
    created_at: datetime


class TrackedObject(MemoryModel):
    object_id: str
    video_id: str
    tracking_id: str
    label: str
    first_seen_ms: int = Field(ge=0)
    last_seen_ms: int = Field(ge=0)


class Observation(MemoryModel):
    observation_id: str
    video_id: str
    object_id: str
    timestamp_ms: int = Field(ge=0)
    frame_index: int = Field(ge=0)
    bounding_box: list[int] = Field(min_length=4, max_length=4)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_uri: str | None = None

    @model_validator(mode="after")
    def validate_box(self):
        left, top, right, bottom = self.bounding_box
        if not (0 <= left < right and 0 <= top < bottom):
            raise ValueError("bounding_box must be half-open [left, top, right, bottom]")
        return self


class Location(MemoryModel):
    location_id: str
    name: str
    type: str


class Event(MemoryModel):
    event_id: str
    video_id: str
    object_id: str
    event_type: Literal["APPEARED", "MOVED", "NO_LONGER_VISIBLE"]
    start_time_ms: int = Field(ge=0)
    end_time_ms: int = Field(ge=0)
    description: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_observation_ids: list[str]

    @model_validator(mode="after")
    def validate_interval(self):
        if self.end_time_ms < self.start_time_ms:
            raise ValueError("event end precedes start")
        return self


SpatialRelationType = Literal["ON", "NEXT_TO", "NEAR", "INSIDE"]
SPATIAL_RELATION_TYPES: tuple[str, ...] = ("ON", "NEXT_TO", "NEAR", "INSIDE")


class Relationship(MemoryModel):
    """A spatial relation verified on sampled frames, holding over [valid_from_ms, valid_to_ms).

    `valid_to_ms` is None while the relation was still holding at the last verification.
    Bounds are only as precise as the frame sampling interval.
    """

    relationship_id: str
    video_id: str
    subject_object_id: str
    target_object_id: str
    relation_type: SpatialRelationType
    valid_from_ms: int = Field(ge=0)
    valid_to_ms: int | None = Field(default=None, ge=0)
    last_verified_ms: int = Field(ge=0)
    evidence_timestamp_ms: int = Field(ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_interval(self):
        if self.valid_to_ms is not None and self.valid_to_ms <= self.valid_from_ms:
            raise ValueError("relationship end must follow its start")
        if self.subject_object_id == self.target_object_id:
            raise ValueError("relationship needs two distinct objects")
        return self


class MemoryBatch(MemoryModel):
    video: Video
    objects: list[TrackedObject]
    observations: list[Observation]
    locations: list[Location] = Field(default_factory=list)
    frame_timestamps_ms: list[int]


class IngestionSummary(MemoryModel):
    video_id: str
    objects_created: int
    observations_processed: int
    events_detected: int
    status: Literal["completed"] = "completed"
