"""Entry point a worker (local background task, Pub/Sub subscriber, ...) calls per job."""

import uuid

from backend.container import AppContainer
from backend.services.video_processing import VideoProcessingService


async def process_video_job(
    container: AppContainer, video_id: uuid.UUID, job_id: uuid.UUID
) -> None:
    async with container.session_factory() as session:
        service = VideoProcessingService(
            session, container.storage, container.sam, container.graph, container.scene
        )
        await service.process(video_id, job_id)
