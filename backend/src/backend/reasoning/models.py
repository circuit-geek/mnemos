from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReasoningModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ReasoningError(Exception):
    """Base class for reasoning failures."""


class ModelResponseError(ReasoningError):
    """The model call failed or returned output that did not validate."""


class Intent(StrEnum):
    LAST_SEEN = "LAST_SEEN"
    CHANGES = "CHANGES"
    OBJECT_HISTORY = "OBJECT_HISTORY"
    SCENE_AT_TIME = "SCENE_AT_TIME"
    RELATIONSHIPS = "RELATIONSHIPS"
    UNSUPPORTED = "UNSUPPORTED"


class QueryIntent(ReasoningModel):
    intent: Intent
    object_label: str | None = None
    time_seconds: float | None = Field(default=None, ge=0)
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    relation_type: Literal["ON", "NEXT_TO", "NEAR", "INSIDE"] | None = None
    before_appearance_of: str | None = None

    @field_validator("object_label", "before_appearance_of")
    @classmethod
    def blank_label_is_none(cls, value):
        return value.strip() or None if value else None

    @field_validator("relation_type", mode="before")
    @classmethod
    def normalize_relation(cls, value):
        # Unknown relation words mean "any relation"; CONTAINS is the inverse of INSIDE.
        value = str(value).strip().upper().replace(" ", "_") if value else None
        value = "INSIDE" if value == "CONTAINS" else value
        return value if value in {"ON", "NEXT_TO", "NEAR", "INSIDE"} else None


class Evidence(ReasoningModel):
    evidence_id: str
    kind: str
    timestamp_ms: int | None = None
    text: str
    graph_id: str | None = None
    evidence_uri: str | None = None


class RetrievalResult(ReasoningModel):
    evidence: list[Evidence] = []
    problem: str | None = None


class ModelAnswer(ReasoningModel):
    answer: str = Field(min_length=1)
    evidence_ids: list[str] = []
    sufficient_evidence: bool


class Answer(ReasoningModel):
    question: str
    intent: QueryIntent
    answer: str
    sufficient_evidence: bool
    evidence: list[Evidence]
