import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import VideoBusyError, VideoNotFoundError
from backend.integrations.neo4j.graph_writer import GraphWriter
from backend.integrations.storage.base import ObjectStorage
from backend.models import ProcessingJob, VideoStatus
from backend.repositories.observations import ObservationRepository
from backend.repositories.tracked_objects import TrackedObjectRepository
from backend.repositories.videos import VideoRepository

logger = logging.getLogger(__name__)

_BUSY = (VideoStatus.UPLOADED, VideoStatus.QUEUED, VideoStatus.PROCESSING)


class VideoDeletionService:
    """Removes a recording everywhere it lives: graph, relational rows, stored file."""

    def __init__(self, session: AsyncSession, storage: ObjectStorage, graph: GraphWriter) -> None:
        self.session = session
        self.storage = storage
        self.graph = graph
        self.videos = VideoRepository(session)
        self.observations = ObservationRepository(session)
        self.tracked_objects = TrackedObjectRepository(session)

    async def delete(self, video_id: uuid.UUID) -> None:
        video = await self.videos.get(video_id)
        if video is None:
            raise VideoNotFoundError(f"Video {video_id} not found")
        if video.status in _BUSY:
            raise VideoBusyError("The video is still being processed; wait until it finishes")
        await self.graph.delete_video_graph(video_id)
        await self.observations.delete_for_video(video_id)
        await self.tracked_objects.delete_for_video(video_id)
        await self.session.execute(
            ProcessingJob.__table__.delete().where(ProcessingJob.video_id == video_id)
        )
        storage_key = video.storage_key
        await self.videos.delete(video)
        await self.session.commit()
        await self.storage.delete_file(storage_key)
        logger.info("Deleted video_id=%s", video_id)
