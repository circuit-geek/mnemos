"""Validate saved SAM experiment artifacts without accessing Neo4j."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .models import MemoryBatch, Observation, TrackedObject, Video


def stable_id(prefix: str, *parts: object) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:24]}"


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read JSON artifact {path}: {exc}") from exc


class ObservationTransformer:
    def load(
        self,
        metadata_path: Path,
        observations_path: Path,
        video_id: str,
        tracking_summary_path: Path | None = None,
    ) -> MemoryBatch:
        metadata_path, observations_path = Path(metadata_path), Path(observations_path)
        metadata, rows = read_json(metadata_path), read_json(observations_path)
        if not isinstance(metadata, dict) or not isinstance(rows, list):
            raise ValueError("Expected metadata object and observations array")
        try:
            width, height = int(metadata["width"]), int(metadata["height"])
            frame_count = int(metadata["frame_count"])
            timestamps = [round(float(t) * 1000) for t in metadata["frame_timestamps_seconds"]]
            duration_ms = (round(float(metadata["duration_seconds"]) * 1000)
                           if metadata.get("duration_seconds") is not None else None)
            filename = Path(metadata["source_video"]).name
            created = datetime.strptime(metadata["created_at_utc"], "%Y%m%d_%H%M%S_%f").replace(tzinfo=timezone.utc)
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Invalid video metadata") from exc
        if width <= 0 or height <= 0 or frame_count <= 0 or len(timestamps) != frame_count:
            raise ValueError("Invalid video dimensions or frame timestamps")
        if any(t < 0 for t in timestamps) or timestamps != sorted(timestamps):
            raise ValueError("Frame timestamps must be nonnegative and ordered")
        if duration_ms is not None and duration_ms < timestamps[-1]:
            raise ValueError("Video duration precedes last frame")
        try:
            video = Video(video_id=video_id, filename=filename, duration_ms=duration_ms, created_at=created)
        except ValidationError as exc:
            raise ValueError("Invalid video identifier") from exc
        normalized = []
        grouped = defaultdict(list)
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Observation must be an object")
            try:
                frame = int(row["frame_index"])
                tracking_id = str(row["tracking_id"])
                label = str(row["label"]).strip()
                box = row["bbox_xyxy"]
                convention = row["bbox_convention"]
                timestamp_ms = round(float(row["timestamp_seconds"]) * 1000)
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError("Malformed observation") from exc
            if not (0 <= frame < frame_count) or not tracking_id or not label:
                raise ValueError("Invalid frame, tracking ID, or label")
            if convention != "pixel half-open [left, top, right, bottom]":
                raise ValueError("Unsupported bounding-box convention")
            if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
                raise ValueError("Bounding box requires four integer coordinates")
            if box[2] > width or box[3] > height:
                raise ValueError("Bounding box exceeds video dimensions")
            if abs(timestamp_ms - timestamps[frame]) > 1:
                raise ValueError("Observation timestamp does not match source frame")
            if (frame, tracking_id) in seen:
                raise ValueError("Duplicate tracking ID on a frame")
            seen.add((frame, tracking_id))
            object_id = stable_id("object", video_id, tracking_id)
            evidence_uri = row.get("evidence_uri")
            if evidence_uri is not None and not isinstance(evidence_uri, str):
                raise ValueError("evidence_uri must be a string")
            if evidence_uri is None and "raw_response.txt" in str(row.get("evidence", "")):
                raw_path = observations_path.parent / "raw_response.txt"
                if raw_path.is_file():
                    evidence_uri = raw_path.resolve().as_uri() + f"#frame={frame}"
            try:
                obs = Observation(
                    observation_id=stable_id("observation", video_id, tracking_id, frame),
                    video_id=video_id, object_id=object_id, timestamp_ms=timestamp_ms,
                    frame_index=frame, bounding_box=box, confidence=row.get("confidence"),
                    evidence_uri=evidence_uri,
                )
            except ValidationError as exc:
                raise ValueError(f"Invalid observation at frame {frame}") from exc
            normalized.append(obs)
            grouped[tracking_id].append((label, obs))
        objects = []
        for tracking_id, entries in sorted(grouped.items()):
            labels = {label for label, _ in entries}
            if len(labels) != 1:
                raise ValueError(f"Conflicting labels for tracking ID {tracking_id}")
            times = [obs.timestamp_ms for _, obs in entries]
            objects.append(TrackedObject(
                object_id=stable_id("object", video_id, tracking_id), video_id=video_id,
                tracking_id=tracking_id, label=entries[0][0],
                first_seen_ms=min(times), last_seen_ms=max(times),
            ))
        if tracking_summary_path is not None:
            summary = read_json(Path(tracking_summary_path))
            if not isinstance(summary, dict) or not isinstance(summary.get("tracks"), dict):
                raise ValueError("Malformed tracking summary")
            if set(summary["tracks"]) != set(grouped):
                raise ValueError("Tracking summary IDs disagree with observations")
            for tracking_id, entries in grouped.items():
                frames = sorted(obs.frame_index for _, obs in entries)
                track = summary["tracks"][tracking_id]
                if not isinstance(track, dict) or any((
                    track.get("first_observed_frame") != frames[0],
                    track.get("last_observed_frame") != frames[-1],
                    track.get("total_frames_detected") != len(frames),
                )):
                    raise ValueError(f"Tracking summary disagrees for ID {tracking_id}")
        return MemoryBatch(video=video, objects=objects,
                           observations=sorted(normalized, key=lambda o: (o.timestamp_ms, o.frame_index, o.object_id)),
                           frame_timestamps_ms=timestamps)
