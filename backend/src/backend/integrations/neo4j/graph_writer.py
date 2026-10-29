import asyncio
import logging
import uuid
from datetime import datetime
from typing import Protocol

from backend.integrations.meta.sam_models import VideoProcessingResult
from backend.memory.models import MemoryBatch, Observation, TrackedObject, Video
from backend.memory.repository import Neo4jMemoryRepository
from backend.memory.transformer import stable_id

logger = logging.getLogger(__name__)


class GraphWriter(Protocol):
    async def write_video_graph(
        self,
        video_id: uuid.UUID,
        filename: str,
        created_at: datetime,
        result: VideoProcessingResult,
    ) -> None: ...

    async def close(self) -> None: ...


class NullGraphWriter:
    """Used when NEO4J_ENABLED=false."""

    async def write_video_graph(self, video_id, filename, created_at, result) -> None:
        logger.info("Neo4j disabled; skipping graph update video_id=%s", video_id)

    async def close(self) -> None:
        return None


class Neo4jGraphWriter:
    """Writes Video/Object/Observation nodes via the existing synchronous repository.

    Only facts present in the SAM output are written; no relationships are inferred.
    The write is idempotent (stable IDs + MERGE), so re-processing does not duplicate.
    """

    def __init__(self, repository: Neo4jMemoryRepository) -> None:
        self.repository = repository

    @classmethod
    async def connect(cls, uri: str, username: str, password: str, database: str | None):
        repository = await asyncio.to_thread(
            Neo4jMemoryRepository.connect, uri, username, password, database
        )
        await asyncio.to_thread(repository.initialize_schema)
        return cls(repository)

    async def write_video_graph(self, video_id, filename, created_at, result) -> None:
        batch = build_memory_batch(video_id, filename, created_at, result)
        await asyncio.to_thread(self.repository.ingest, batch, [])

    async def close(self) -> None:
        await asyncio.to_thread(self.repository.close)


def build_memory_batch(
    video_id: uuid.UUID, filename: str, created_at: datetime, result: VideoProcessingResult
) -> MemoryBatch:
    vid = str(video_id)
    object_ids = {o.tracking_id: stable_id("object", vid, o.tracking_id) for o in result.objects}
    observations = [
        Observation(
            observation_id=stable_id("observation", vid, o.tracking_id, o.frame_number),
            video_id=vid,
            object_id=object_ids[o.tracking_id],
            timestamp_ms=round(o.timestamp_seconds * 1000),
            frame_index=o.frame_number,
            bounding_box=o.bbox,
            confidence=o.confidence,
            evidence_uri=o.evidence_uri,
        )
        for o in result.observations
    ]
    return MemoryBatch(
        video=Video(
            video_id=vid,
            filename=filename,
            duration_ms=(
                round(result.duration_seconds * 1000)
                if result.duration_seconds is not None
                else None
            ),
            created_at=created_at,
        ),
        objects=[
            TrackedObject(
                object_id=object_ids[o.tracking_id],
                video_id=vid,
                tracking_id=o.tracking_id,
                label=o.label or "unknown",
                first_seen_ms=round(o.first_seen_seconds * 1000),
                last_seen_ms=round(o.last_seen_seconds * 1000),
            )
            for o in result.objects
        ],
        observations=observations,
        frame_timestamps_ms=sorted({o.timestamp_ms for o in observations}),
    )
