#!/usr/bin/env python3
"""Re-run only the spatial analysis for an already processed video (no SAM, no re-upload).

Useful after changing the scene prompt or SCENE_* settings. It reads the video
file, objects and observations that are already stored, recomputes the spatial relations with
the current settings, and replaces the video's relations in Neo4j.

  uv run python scripts/reanalyze_scene.py <video_id> [--dry-run]
"""

import argparse
import asyncio
import uuid
from datetime import UTC, datetime

from backend.core.config import get_settings
from backend.db.session import create_engine, create_session_factory
from backend.integrations.storage.factory import create_storage
from backend.memory.models import MemoryBatch, Observation, TrackedObject, Video
from backend.memory.repository import Neo4jMemoryRepository
from backend.models import Video as VideoRow
from backend.reasoning.muse_client import MuseClient
from backend.scene.scene_service import SceneAnalyzer


def describe(relationships, labels):
    for r in relationships:
        end = "open" if r.valid_to_ms is None else f"{r.valid_to_ms / 1000:.1f}"
        print(f"  {labels[r.subject_object_id]:9} {r.relation_type:8} {labels[r.target_object_id]:9}"
              f" {r.valid_from_ms / 1000:5.1f} -> {end}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_id", type=uuid.UUID)
    parser.add_argument("--dry-run", action="store_true", help="show the result, do not save it")
    args = parser.parse_args()
    settings = get_settings()
    if not (settings.neo4j_enabled and settings.meta_api_key):
        parser.error("NEO4J_ENABLED=true and META_API_KEY are required")

    engine = create_engine(settings.database_url)
    async with create_session_factory(engine)() as session:
        row = await session.get(VideoRow, args.video_id)
    await engine.dispose()
    if row is None or not row.width or not row.height:
        parser.error("video not found, or it has no stored frame size")

    memory = Neo4jMemoryRepository.connect(settings.neo4j_uri, settings.neo4j_username,
                                           settings.neo4j_password, settings.neo4j_database)
    try:
        vid = str(args.video_id)
        objects = [TrackedObject(**o) for o in memory.get_video_objects(vid)]
        observations = [Observation(**o) for o in memory.get_video_observations(vid)]
        labels = {o.object_id: o.label for o in objects}
        before = memory.get_video_relationships(vid)
        print(f"{row.original_filename}: {len(objects)} objects, {len(observations)} observations, "
              f"{len(before)} stored relations")
        batch = MemoryBatch(
            video=Video(video_id=vid, filename=row.original_filename,
                        duration_ms=round((row.duration_seconds or 0) * 1000), created_at=datetime.now(UTC)),
            objects=objects, observations=observations,
            frame_timestamps_ms=sorted({o.timestamp_ms for o in observations}))
        analyzer = SceneAnalyzer(
            MuseClient(settings.meta_api_key, settings.muse_model, timeout=settings.muse_timeout_seconds),
            interval_ms=settings.scene_sample_interval_ms, min_confidence=settings.scene_min_confidence,
            concurrency=settings.scene_concurrency)
        async with create_storage(settings).open_local_copy(row.storage_key) as path:
            relationships = await analyzer.analyze(path, batch, (row.width, row.height))
        print("new relations:")
        describe(relationships, labels)
        if args.dry_run:
            print("(dry run: nothing saved)")
        else:
            memory.replace_relationships(vid, relationships)
            print(f"saved {len(relationships)} relations")
    finally:
        memory.close()


if __name__ == "__main__":
    asyncio.run(main())
