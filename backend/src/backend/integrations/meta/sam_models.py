"""Internal, provider-independent result of running SAM over a video."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrackedObjectResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tracking_id: str = Field(min_length=1)
    label: str | None = None
    first_seen_seconds: float = Field(ge=0)
    last_seen_seconds: float = Field(ge=0)


class ObservationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tracking_id: str = Field(min_length=1)
    timestamp_seconds: float = Field(ge=0)
    frame_number: int = Field(ge=0)
    label: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    # Pixel half-open [left, top, right, bottom].
    bbox: list[int] = Field(min_length=4, max_length=4)
    evidence_uri: str | None = None


class VideoProcessingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    duration_seconds: float | None = Field(default=None, ge=0)
    frame_count: int | None = None
    width: int | None = None
    height: int | None = None
    objects: list[TrackedObjectResult] = Field(default_factory=list)
    observations: list[ObservationResult] = Field(default_factory=list)

    @model_validator(mode="after")
    def observations_reference_known_objects(self):
        known = {o.tracking_id for o in self.objects}
        unknown = {o.tracking_id for o in self.observations} - known
        if unknown:
            raise ValueError(f"Observations reference unknown tracking IDs: {sorted(unknown)}")
        return self
