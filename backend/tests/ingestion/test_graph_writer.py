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
