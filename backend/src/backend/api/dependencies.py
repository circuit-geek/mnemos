from collections.abc import AsyncIterator
from functools import partial

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.container import AppContainer
from backend.services.video_ingestion import VideoIngestionService
from backend.services.video_queries import VideoQueryService
from backend.workers.dispatcher import BackgroundTasksDispatcher
from backend.workers.video_worker import process_video_job


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


async def get_session(
    container: AppContainer = Depends(get_container),
) -> AsyncIterator[AsyncSession]:
    async with container.session_factory() as session:
        yield session


def get_ingestion_service(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_container),
) -> VideoIngestionService:
    dispatcher = BackgroundTasksDispatcher(background_tasks, partial(process_video_job, container))
    return VideoIngestionService(
        session, container.storage, dispatcher, container.settings.max_upload_bytes
    )


def get_query_service(session: AsyncSession = Depends(get_session)) -> VideoQueryService:
    return VideoQueryService(session)
