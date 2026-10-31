from typing import Any

from pydantic import BaseModel, Field

from backend.reasoning.models import Answer


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class MemoryObject(BaseModel):
    object_id: str
    tracking_id: str
    label: str
    first_seen_ms: int
    last_seen_ms: int


class MemoryObservation(BaseModel):
    observation_id: str
    timestamp_ms: int
    frame_index: int
    bounding_box: list[int]
    confidence: float | None = None
    evidence_uri: str | None = None


class MemoryEvent(BaseModel):
    event_id: str
    object_id: str
    # Second object of a relationship event; the relationship itself is `relationship_id`.
    related_object_id: str | None = None
    relationship_id: str | None = None
    event_type: str
    start_time_ms: int
    end_time_ms: int
    description: str
    confidence: float | None = None


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class MemoryRelationship(BaseModel):
    relationship_id: str
    subject_object_id: str
    target_object_id: str
    relation_type: str
    valid_from_ms: int
    valid_to_ms: int | None = None
    last_verified_ms: int
    evidence_timestamp_ms: int
    confidence: float | None = None
    reason: str | None = None
    evidence_uri: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    video_id: str
    at_ms: int | None
    nodes: list[GraphNode]
    edges: list[GraphEdge]


AskResponse = Answer


class FullObservation(MemoryObservation):
    object_id: str


class MemoryBundle(BaseModel):
    """Everything the explorer needs for one recording; the client derives any moment from it."""

    video_id: str
    objects: list[MemoryObject]
    observations: list[FullObservation]
    events: list[MemoryEvent]
    relationships: list[MemoryRelationship]
