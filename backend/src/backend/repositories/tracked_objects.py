import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import TrackedObject


class TrackedObjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, objects: list[TrackedObject]) -> None:
        self.session.add_all(objects)
        await self.session.flush()

    async def delete_for_video(self, video_id: uuid.UUID) -> None:
        await self.session.execute(delete(TrackedObject).where(TrackedObject.video_id == video_id))
