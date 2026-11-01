"""Deterministic, observation-grounded temporal events."""

import math
from collections import defaultdict

from .models import Event, MemoryBatch, Observation
from .transformer import stable_id


def center(observation: Observation) -> tuple[float, float]:
    left, top, right, bottom = observation.bounding_box
    return ((left + right) / 2, (top + bottom) / 2)


class EventDetector:
    def __init__(self, movement_threshold_px: float = 50, missing_threshold_ms: int = 1000,
                 movement_onset_px: float = 15, movement_merge_gap_ms: int = 1000):
        if min(movement_threshold_px, missing_threshold_ms, movement_onset_px,
               movement_merge_gap_ms) <= 0:
            raise ValueError("Event thresholds must be positive")
        self.movement_onset_px = movement_onset_px
        self.movement_merge_gap_ms = movement_merge_gap_ms
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
            onset = None  # first observation clearly away from the anchor: when motion began
            moves = []
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
                    onset = None
                    continue
                shift = math.dist(center(anchor), center(current))
                if onset is None and shift >= self.movement_onset_px:
                    onset = current
                if shift >= self.movement_threshold_px:
                    # A one-frame jump has no earlier onset: it happened since the anchor.
                    moves.append((onset if onset is not None and onset is not current else anchor, current))
                    anchor = current
                    onset = None
                previous = current
            events.extend(self._movement_events(batch.video.video_id, tracked, moves))
            if previous.frame_index < len(batch.frame_timestamps_ms) - 1:
                first_missing = batch.frame_timestamps_ms[previous.frame_index + 1]
                end = batch.video.duration_ms
                if end is not None and end - first_missing >= self.missing_threshold_ms:
                    events.append(self._event(batch.video.video_id, tracked.object_id,
                                              "NO_LONGER_VISIBLE", first_missing, end,
                                              f"{tracked.label} not detected through recording end",
                                              [previous.observation_id]))
        return sorted(events, key=lambda e: (e.start_time_ms, e.end_time_ms, e.event_type, e.event_id))

    def _movement_events(self, video_id, tracked, moves):
        """Movements that follow each other within the merge gap are one continuous movement."""
        segments = []  # [start, end, distance travelled along the path]
        for start, end in moves:
            travelled = math.dist(center(start), center(end))
            if segments and start.timestamp_ms - segments[-1][1].timestamp_ms <= self.movement_merge_gap_ms:
                segments[-1][1] = end
                segments[-1][2] += travelled
            else:
                segments.append([start, end, travelled])
        return [
            self._event(video_id, tracked.object_id, "MOVED", start.timestamp_ms, end.timestamp_ms,
                        f"{tracked.label} moved in the frame (about {travelled:.0f} px travelled)",
                        [start.observation_id, end.observation_id])
            for start, end, travelled in segments
        ]

    @staticmethod
    def _event(video_id, object_id, kind, start, end, description, sources):
        return Event(event_id=stable_id("event", video_id, object_id, kind, start, end),
                     video_id=video_id, object_id=object_id, event_type=kind,
                     start_time_ms=start, end_time_ms=end,
                     description=description, source_observation_ids=sources)
