"""Deterministic, observation-grounded temporal events."""

import math
from collections import defaultdict

from .models import Event, MemoryBatch, Observation
from .transformer import stable_id


def center(observation: Observation) -> tuple[float, float]:
    left, top, right, bottom = observation.bounding_box
    return ((left + right) / 2, (top + bottom) / 2)


class EventDetector:
    def __init__(self, movement_threshold_px: float = 50, missing_threshold_ms: int = 1000):
        if movement_threshold_px <= 0 or missing_threshold_ms <= 0:
            raise ValueError("Event thresholds must be positive")
        self.movement_threshold_px = movement_threshold_px
        self.missing_threshold_ms = missing_threshold_ms

    def detect(self, batch: MemoryBatch) -> list[Event]:
        by_object = defaultdict(list)
        for observation in batch.observations:
            by_object[observation.object_id].append(observation)
        events = []
        for tracked in batch.objects:
            history = sorted(by_object[tracked.object_id], key=lambda item: item.frame_index)
            if not history:
                continue
            first = history[0]
            events.append(self._event(batch.video.video_id, tracked.object_id, "APPEARED",
                                      first.timestamp_ms, first.timestamp_ms,
                                      f"{tracked.label} first detected", [first.observation_id]))
            anchor = first
            previous = first
            for current in history[1:]:
                if current.frame_index > previous.frame_index + 1:
                    first_missing = batch.frame_timestamps_ms[previous.frame_index + 1]
                    if current.timestamp_ms - first_missing >= self.missing_threshold_ms:
                        events.append(self._event(batch.video.video_id, tracked.object_id,
                                                  "NO_LONGER_VISIBLE", first_missing, current.timestamp_ms,
                                                  f"{tracked.label} not detected before next observation",
                                                  [previous.observation_id, current.observation_id]))
                    # A center jump across unseen frames cannot establish motion.
                    anchor = current
                    previous = current
                    continue
                if math.dist(center(anchor), center(current)) >= self.movement_threshold_px:
                    events.append(self._event(batch.video.video_id, tracked.object_id, "MOVED",
                                              anchor.timestamp_ms, current.timestamp_ms,
                                              f"{tracked.label} bounding-box center moved at least {self.movement_threshold_px:g} px",
                                              [anchor.observation_id, current.observation_id]))
                    anchor = current
                previous = current
            if previous.frame_index < len(batch.frame_timestamps_ms) - 1:
                first_missing = batch.frame_timestamps_ms[previous.frame_index + 1]
                end = batch.video.duration_ms
                if end is not None and end - first_missing >= self.missing_threshold_ms:
                    events.append(self._event(batch.video.video_id, tracked.object_id,
                                              "NO_LONGER_VISIBLE", first_missing, end,
                                              f"{tracked.label} not detected through recording end",
                                              [previous.observation_id]))
        return sorted(events, key=lambda e: (e.start_time_ms, e.end_time_ms, e.event_type, e.event_id))

    @staticmethod
    def _event(video_id, object_id, kind, start, end, description, sources):
        return Event(event_id=stable_id("event", video_id, object_id, kind, start, end),
                     video_id=video_id, object_id=object_id, event_type=kind,
                     start_time_ms=start, end_time_ms=end,
                     description=description, source_observation_ids=sources)
