"""Scene intelligence: ask Muse Spark which spatial relations hold on sampled frames."""

import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from backend.core.exceptions import FrameNotFoundError
from backend.integrations.media.frames import extract_frame_jpeg
from backend.memory.models import MemoryBatch, Observation, Relationship
from backend.reasoning.models import ReasoningError
from backend.scene.intervals import Detected, Sample, build_relationships

logger = logging.getLogger(__name__)

SCENE_INSTRUCTIONS = """You describe spatial relations between tracked objects in one video frame.
The input lists the objects visible at this moment: an id, a label, and an approximate box
[left, top, right, bottom] as fractions of the frame width/height from a separate tracker.
Boxes are hints only; decide from what you can see in the image.
Return ONLY JSON: {"relationships": [{"subject": id, "relation": R, "object": id,
"confidence": 0..1, "reason": short string}]}. R is one of:
- ON: subject rests on top of object.
- NEXT_TO: side by side, adjacent (symmetric: report each pair once).
- NEAR: close together but not adjacent (symmetric: report each pair once).
- INSIDE: subject is inside object (in a bag, cup, box, drawer).
- CONTAINS: inverse of INSIDE.
Rules: use only the given ids; only report relations that are clearly visible; never infer a
relation from overlapping boxes alone; report the single best relation per pair; return an empty
list when no relation is clear."""


class _Item(BaseModel):
    subject: str
    relation: Literal["ON", "NEXT_TO", "NEAR", "INSIDE", "CONTAINS"]
    object: str
    confidence: float = 0.0
    reason: str | None = None


class SceneAnalyzer:
    def __init__(self, muse, interval_ms: int = 2000, tolerance_ms: int = 500,
                 min_confidence: float = 0.6, concurrency: int = 4, max_frame_width: int = 960):
        if interval_ms <= 0:
            raise ValueError("interval_ms must be positive")
        self.muse = muse
        self.interval_ms = interval_ms
        self.tolerance_ms = tolerance_ms
        self.min_confidence = min_confidence
        self.max_frame_width = max_frame_width
        self._slots = asyncio.Semaphore(concurrency)

    async def analyze(self, video_path: Path, batch: MemoryBatch,
                      frame_size: tuple[int | None, int | None] = (None, None)) -> list[Relationship]:
        by_object: dict[str, list[Observation]] = defaultdict(list)
        for obs in batch.observations:
            by_object[obs.object_id].append(obs)
        ordered = sorted(batch.objects, key=lambda o: (o.first_seen_ms, o.object_id))
        counts: dict[str, int] = defaultdict(int)
        aliases: dict[str, str] = {}
        for tracked in ordered:
            counts[tracked.label] += 1
            aliases[tracked.object_id] = f"{tracked.label.replace(' ', '_')}_{counts[tracked.label]}"
        labels = {o.object_id: o.label for o in ordered}

        end_ms = batch.video.duration_ms or max((o.timestamp_ms for o in batch.observations),
                                                default=0)
        jobs = []
        for t in range(0, end_ms + 1, self.interval_ms):
            visible = self._visible_at(by_object, t)
            if len(visible) >= 2:
                jobs.append((t, visible))
        logger.info("Scene analysis video_id=%s samples=%d interval_ms=%d",
                    batch.video.video_id, len(jobs), self.interval_ms)
        samples = await asyncio.gather(*(
            self._sample(str(video_path), t, visible, aliases, labels, frame_size)
            for t, visible in jobs))
        relationships = build_relationships(batch.video.video_id, list(samples))
        logger.info("Scene analysis done video_id=%s failed_samples=%d relationships=%d",
                    batch.video.video_id, sum(not s.verified for s in samples), len(relationships))
        return relationships

    def _visible_at(self, by_object: dict[str, list[Observation]], t: int) -> dict[str, Observation]:
        visible = {}
        for object_id, observations in by_object.items():
            nearest = min(observations, key=lambda o: abs(o.timestamp_ms - t))
            if abs(nearest.timestamp_ms - t) <= self.tolerance_ms:
                visible[object_id] = nearest
        return visible

    async def _sample(self, path, t, visible, aliases, labels, frame_size) -> Sample:
        ids = frozenset(visible)
        width, height = frame_size
        objects = []
        for object_id, obs in visible.items():
            item = {"id": aliases[object_id], "label": labels[object_id]}
            if width and height:
                left, top, right, bottom = obs.bounding_box
                item["box"] = [round(left / width, 3), round(top / height, 3),
                               round(right / width, 3), round(bottom / height, 3)]
            objects.append(item)
        try:
            async with self._slots:
                frame = await extract_frame_jpeg(path, t, self.max_frame_width)
                raw = await asyncio.to_thread(
                    self.muse.generate_json, SCENE_INSTRUCTIONS,
                    {"frame_time_seconds": t / 1000, "objects": objects}, images=[frame])
        except (FrameNotFoundError, ReasoningError) as error:
            logger.warning("Scene sample at %dms skipped: %s", t, error)
            return Sample(t, ids, verified=False)
        return Sample(t, ids, self._detections(raw, {a: o for o, a in aliases.items()
                                                      if o in visible}))

    def _detections(self, raw: dict, by_alias: dict[str, str]) -> list[Detected]:
        found = []
        entries = raw.get("relationships")
        for entry in entries if isinstance(entries, list) else []:
            try:
                item = _Item.model_validate(entry)
            except ValidationError:
                logger.warning("Dropped malformed relationship entry")
                continue
            subject, target = by_alias.get(item.subject), by_alias.get(item.object)
            if subject is None or target is None or subject == target:
                logger.warning("Dropped relationship with unknown or identical ids")
                continue
            if not 0 <= item.confidence <= 1 or item.confidence < self.min_confidence:
                continue
            relation = item.relation
            if relation == "CONTAINS":  # stored once, as the inverse INSIDE
                relation, subject, target = "INSIDE", target, subject
            found.append(Detected(relation, subject, target, item.confidence, item.reason))
        return found
