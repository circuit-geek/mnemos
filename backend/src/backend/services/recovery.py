"""Jobs run in-process, so a restart abandons whatever was in flight; make that visible."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models import JobStatus, ProcessingJob, Video, VideoStatus

logger = logging.getLogger(__name__)

_UNFINISHED_VIDEO = (VideoStatus.UPLOADED, VideoStatus.QUEUED, VideoStatus.PROCESSING)
_UNFINISHED_JOB = (JobStatus.PENDING, JobStatus.RUNNING)
MESSAGE = "Interrupted by a backend restart before it finished. Upload the video again."


async def fail_interrupted_jobs(session_factory: async_sessionmaker[AsyncSession]) -> int:
    """Mark videos and jobs left unfinished by a previous process as failed; return how many."""
    async with session_factory() as session:
        videos = (
            await session.execute(select(Video).where(Video.status.in_(_UNFINISHED_VIDEO)))
        ).scalars().all()
        for video in videos:
            video.status = VideoStatus.FAILED
        jobs = (
            await session.execute(
                select(ProcessingJob).where(ProcessingJob.status.in_(_UNFINISHED_JOB))
            )
        ).scalars().all()
        for job in jobs:
            job.status, job.stage, job.stage_detail = JobStatus.FAILED, "failed", None
            job.error_message = MESSAGE
        await session.commit()
    if videos:
        logger.warning("Marked %d interrupted video(s) as failed after restart", len(videos))
    return len(videos)
