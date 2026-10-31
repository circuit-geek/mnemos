"""Turn per-frame relation detections into validity intervals (pure; no I/O)."""

from dataclasses import dataclass, field

from backend.memory.models import Relationship
from backend.memory.transformer import stable_id

SYMMETRIC = {"NEXT_TO", "NEAR"}


@dataclass(frozen=True)
class Detected:
    relation_type: str
    subject_id: str
    target_id: str
    confidence: float | None = None
    reason: str | None = None

    def key(self) -> tuple[str, str, str]:
        subject, target = self.subject_id, self.target_id
        if self.relation_type in SYMMETRIC and subject > target:
            subject, target = target, subject
        return self.relation_type, subject, target


@dataclass(frozen=True)
class Sample:
    """One analysed frame. `verified` is False when the model call failed or was unusable."""

    timestamp_ms: int
    visible: frozenset[str]
    detections: list[Detected] = field(default_factory=list)
    verified: bool = True


def build_relationships(video_id: str, samples: list[Sample]) -> list[Relationship]:
    """A relation opens at its first detection and closes only at a verified sample where both
    objects are visible and it is no longer reported. Visibility gaps and failed samples never
    close it: absence from view is not evidence the relation ended."""
    open_state: dict[tuple, dict] = {}
    done: list[Relationship] = []

    def finish(state: dict, valid_to: int | None) -> None:
        relation_type, subject, target = state["key"]
        done.append(Relationship(
            relationship_id=stable_id("relationship", video_id, relation_type, subject, target,
                                      state["from"]),
            video_id=video_id, subject_object_id=subject, target_object_id=target,
            relation_type=relation_type, valid_from_ms=state["from"], valid_to_ms=valid_to,
            last_verified_ms=state["last"], evidence_timestamp_ms=state["evidence"],
            confidence=state["confidence"], reason=state["reason"],
        ))

    for sample in sorted(samples, key=lambda s: s.timestamp_ms):
        if not sample.verified:
            continue
        reported = {d.key(): d for d in sample.detections}
        for key in list(open_state):
            _, subject, target = key
            if key in reported:
                open_state[key]["last"] = sample.timestamp_ms
            elif subject in sample.visible and target in sample.visible:
                finish(open_state.pop(key), sample.timestamp_ms)
        for key, detection in reported.items():
            if key not in open_state:
                open_state[key] = {
                    "key": key, "from": sample.timestamp_ms, "last": sample.timestamp_ms,
                    "evidence": sample.timestamp_ms, "confidence": detection.confidence,
                    "reason": detection.reason,
                }
    for state in open_state.values():
        finish(state, None)
    return sorted(done, key=lambda r: (r.valid_from_ms, r.relationship_id))
