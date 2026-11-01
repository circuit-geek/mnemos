import uuid
from datetime import UTC, datetime

from backend.integrations.meta.sam_parser import parse_sam_artifacts
from backend.integrations.neo4j.graph_writer import build_memory_batch

from .conftest import FIXTURE_DIR


def test_memory_batch_is_built_from_result_without_inventing_data():
    video_id = uuid.uuid4()
    batch = build_memory_batch(
        video_id, "clip.mp4", datetime.now(UTC), parse_sam_artifacts(FIXTURE_DIR)
    )

    assert batch.video.video_id == str(video_id)
    assert {o.tracking_id for o in batch.objects} == {"1", "2"}
    assert len(batch.observations) == 5
    assert all(o.object_id in {t.object_id for t in batch.objects} for o in batch.observations)


async def test_writer_ingests_detected_events_with_batch():
    from backend.integrations.neo4j.graph_writer import Neo4jGraphWriter

    class Repo:
        def ingest(self, batch, events):
            self.batch, self.events = batch, events

    repo = Repo()
    await Neo4jGraphWriter(repo).write_video_graph(
        uuid.uuid4(), "clip.mp4", datetime.now(UTC), parse_sam_artifacts(FIXTURE_DIR)
    )

    assert {e.event_type for e in repo.events} >= {"APPEARED"}
    assert len(repo.events) >= len(repo.batch.objects)


def test_frames_with_no_detections_do_not_shift_event_times():
    """A lone object vanishes for several whole frames; later frame numbers must still map to
    the right timestamps (previously the timestamp list skipped undetected frames)."""
    from backend.integrations.meta.sam_models import (
        ObservationResult,
        TrackedObjectResult,
        VideoProcessingResult,
    )
    from backend.memory.events import EventDetector

    stamps = [i * 0.5 for i in range(10)]  # frames at 0.0 .. 4.5 s
    seen = [0, 1, 7, 8, 9]  # undetected for frames 2-6 (1.0 s to 3.5 s)
    result = VideoProcessingResult(
        duration_seconds=4.5, width=100, height=100, frame_timestamps_seconds=stamps,
        objects=[TrackedObjectResult(tracking_id="1", label="mug", first_seen_seconds=0,
                                     last_seen_seconds=4.5)],
        observations=[ObservationResult(tracking_id="1", label="mug", timestamp_seconds=stamps[f],
                                        frame_number=f, bbox=[10, 10, 20, 20]) for f in seen])
    batch = build_memory_batch(uuid.uuid4(), "c.mp4", datetime.now(UTC), result)

    assert batch.frame_timestamps_ms == [int(t * 1000) for t in stamps]
    [gone] = [e for e in EventDetector().detect(batch) if e.event_type == "NO_LONGER_VISIBLE"]
    assert (gone.start_time_ms, gone.end_time_ms) == (1000, 3500)
