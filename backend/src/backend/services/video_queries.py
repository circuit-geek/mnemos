import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import VideoNotFoundError
from backend.models import Observation, ProcessingJob, Video
from backend.repositories.observations import ObservationRepository
from backend.repositories.processing_jobs import ProcessingJobRepository
from backend.repositories.videos import VideoRepository


class VideoQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.videos = VideoRepository(session)
        self.jobs = ProcessingJobRepository(session)
        self.observations = ObservationRepository(session)

    async def get_video(self, video_id: uuid.UUID) -> tuple[Video, ProcessingJob | None]:
        video = await self._require(video_id)
        return video, await self.jobs.get_latest_for_video(video_id)

    async def list_observations(
        self, video_id: uuid.UUID, limit: int, offset: int
    ) -> list[Observation]:
        await self._require(video_id)
        return await self.observations.list_for_video(video_id, limit, offset)

    async def _require(self, video_id: uuid.UUID) -> Video:
        video = await self.videos.get(video_id)
        if video is None:
            raise VideoNotFoundError(f"Video {video_id} not found")
        return video
