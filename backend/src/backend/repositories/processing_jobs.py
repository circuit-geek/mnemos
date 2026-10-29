import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import JobStatus, ProcessingJob


class ProcessingJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, job: ProcessingJob) -> ProcessingJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def get(self, job_id: uuid.UUID) -> ProcessingJob | None:
        return await self.session.get(ProcessingJob, job_id)

    async def get_latest_for_video(self, video_id: uuid.UUID) -> ProcessingJob | None:
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.video_id == video_id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def mark_running(self, job: ProcessingJob) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.error_message = None
        await self.session.flush()

    async def mark_completed(self, job: ProcessingJob) -> None:
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, job: ProcessingJob, error_message: str) -> None:
        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        await self.session.flush()
