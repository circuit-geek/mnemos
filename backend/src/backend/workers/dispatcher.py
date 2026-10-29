"""Boundary between "a video needs processing" and "something will process it".

Services call `ProcessingDispatcher.dispatch_video_processing` and nothing else. The
local implementation runs the handler in-process via FastAPI BackgroundTasks, so jobs
do not survive a restart. To move to Google Cloud Pub/Sub, add a dispatcher that
publishes `{video_id, job_id}` to a topic and have a subscriber call
`workers.video_worker.process_video_job` with those IDs; no service code changes.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import BackgroundTasks

ProcessingHandler = Callable[[uuid.UUID, uuid.UUID], Awaitable[None]]


class ProcessingDispatcher(Protocol):
    async def dispatch_video_processing(self, video_id: uuid.UUID, job_id: uuid.UUID) -> None:
        """Request asynchronous processing; must return without doing the work inline."""


class BackgroundTasksDispatcher:
    def __init__(self, background_tasks: BackgroundTasks, handler: ProcessingHandler) -> None:
        self._background_tasks = background_tasks
        self._handler = handler

    async def dispatch_video_processing(self, video_id: uuid.UUID, job_id: uuid.UUID) -> None:
        self._background_tasks.add_task(self._handler, video_id, job_id)
