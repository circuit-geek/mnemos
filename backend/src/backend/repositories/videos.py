import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Video, VideoStatus


class VideoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, video: Video) -> Video:
        self.session.add(video)
        await self.session.flush()
        return video

    async def get(self, video_id: uuid.UUID) -> Video | None:
        return await self.session.get(Video, video_id)

    async def set_status(self, video: Video, status: VideoStatus) -> None:
        video.status = status
        await self.session.flush()
