import json
from pathlib import Path

import pytest

from backend.memory.events import EventDetector
from backend.memory.repository import Neo4jMemoryRepository
from backend.memory.service import MemoryIngestionService
from backend.memory.transformer import ObservationTransformer


def artifacts(tmp_path: Path) -> tuple[Path, Path]:
    metadata = {
        "source_video": str(tmp_path / "clip.mp4"), "width": 100, "height": 80,
        "frame_count": 6, "duration_seconds": 0.6,
        "frame_timestamps_seconds": [0, 0.1, 0.2, 0.3, 0.4, 0.5],
        "created_at_utc": "20261028_010000_000000",
    }
    observations = [
        {"frame_index": 0, "timestamp_seconds": 0, "tracking_id": "0", "label": "mug", "bbox_xyxy": [0, 0, 10, 10], "bbox_convention": "pixel half-open [left, top, right, bottom]", "evidence": "SAM response in raw_response.txt"},
        {"frame_index": 1, "timestamp_seconds": 0.1, "tracking_id": "0", "label": "mug", "bbox_xyxy": [1, 0, 11, 10], "bbox_convention": "pixel half-open [left, top, right, bottom]"},
        {"frame_index": 2, "timestamp_seconds": 0.2, "tracking_id": "0", "label": "mug", "bbox_xyxy": [21, 0, 31, 10], "bbox_convention": "pixel half-open [left, top, right, bottom]"},
        {"frame_index": 5, "timestamp_seconds": 0.5, "tracking_id": "0", "label": "mug", "bbox_xyxy": [60, 0, 70, 10], "bbox_convention": "pixel half-open [left, top, right, bottom]"},
    ]
    meta_path, obs_path = tmp_path / "metadata.json", tmp_path / "observations.json"
    meta_path.write_text(json.dumps(metadata))
    obs_path.write_text(json.dumps(observations))
    (tmp_path / "raw_response.txt").write_text("source")
    return meta_path, obs_path


def test_transformer_is_deterministic_and_scopes_tracking_ids(tmp_path):
    meta_path, obs_path = artifacts(tmp_path)
    transformer = ObservationTransformer()
    first = transformer.load(meta_path, obs_path, "video_a")
    repeated = transformer.load(meta_path, obs_path, "video_a")
    other = transformer.load(meta_path, obs_path, "video_b")
    assert first.model_dump() == repeated.model_dump()
    assert first.objects[0].object_id != other.objects[0].object_id
    assert first.observations[2].timestamp_ms == 200
    assert first.observations[2].bounding_box == [21, 0, 31, 10]
    assert first.observations[0].evidence_uri.endswith("raw_response.txt#frame=0")
    assert first.locations == []


def test_transformer_rejects_malformed_artifacts(tmp_path):
    meta_path, obs_path = artifacts(tmp_path)
    rows = json.loads(obs_path.read_text())
    rows[0]["bbox_xyxy"] = [0, 0, 101, 10]
    obs_path.write_text(json.dumps(rows))
    with pytest.raises(ValueError):
        ObservationTransformer().load(meta_path, obs_path, "video_a")


def test_events_are_ordered_thresholded_and_stable(tmp_path):
    batch = ObservationTransformer().load(*artifacts(tmp_path), "video_a")
    detector = EventDetector(movement_threshold_px=15, missing_threshold_ms=200)
    events = detector.detect(batch)
    assert [event.event_type for event in events] == ["APPEARED", "MOVED", "NO_LONGER_VISIBLE"]
    assert [(event.start_time_ms, event.end_time_ms) for event in events] == [(0, 0), (0, 200), (300, 500)]
    assert events == detector.detect(batch)
    assert len({event.event_id for event in events}) == len(events)


def test_ingestion_service_uses_validated_batch_and_reports_real_creates(tmp_path):
    class Repository:
        calls = 0

        def initialize_schema(self):
            pass

        def ingest(self, batch, events):
            self.calls += 1
            assert len(batch.observations) == 4
            assert len(events) == 3
            return 1 if self.calls == 1 else 0

    repository = Repository()
    service = MemoryIngestionService(repository, event_detector=EventDetector(15, 200))
    meta_path, obs_path = artifacts(tmp_path)
    first = service.ingest(meta_path, obs_path, "video_a")
    repeated = service.ingest(meta_path, obs_path, "video_a")
    assert first.model_dump() == {"video_id": "video_a", "objects_created": 1,
                                  "observations_processed": 4, "events_detected": 3,
                                  "status": "completed"}
    assert repeated.objects_created == 0


def test_repository_batches_parameterized_observations(tmp_path):
    batch = ObservationTransformer().load(*artifacts(tmp_path), "video_a")

    class Result:
        def consume(self):
            return type("Summary", (), {"counters": type("Counters", (), {"nodes_created": 4})()})()

    class Tx:
        def run(self, statement, **parameters):
            assert "UNWIND $rows" in statement
            assert "MERGE (obs:Observation" in statement
            assert len(parameters["rows"]) == 4
            assert parameters["rows"][0]["object_id"] == batch.objects[0].object_id
            return Result()

    assert Neo4jMemoryRepository._save_observations(Tx(), batch.observations) == 4
