import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import TrackedObject, Video, VideoStatus


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

    async def list_recent(self, limit: int) -> list[tuple[Video, int]]:
        """Newest first, each with its tracked-object count."""
        counts = (
            select(TrackedObject.video_id, func.count().label("n"))
            .group_by(TrackedObject.video_id)
            .subquery()
        )
        stmt = (
            select(Video, func.coalesce(counts.c.n, 0))
            .outerjoin(counts, counts.c.video_id == Video.id)
            .order_by(Video.created_at.desc())
            .limit(limit)
        )
        return [(video, n) for video, n in (await self.session.execute(stmt)).all()]
