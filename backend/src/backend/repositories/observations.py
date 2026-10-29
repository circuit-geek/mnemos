import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Observation


class ObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, observations: list[Observation]) -> None:
        self.session.add_all(observations)
        await self.session.flush()

    async def list_for_video(
        self, video_id: uuid.UUID, limit: int, offset: int
    ) -> list[Observation]:
        stmt = (
            select(Observation)
            .where(Observation.video_id == video_id)
            .order_by(Observation.timestamp_seconds, Observation.frame_number, Observation.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def delete_for_video(self, video_id: uuid.UUID) -> None:
        await self.session.execute(delete(Observation).where(Observation.video_id == video_id))
