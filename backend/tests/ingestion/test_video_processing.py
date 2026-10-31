import io

import pytest
from sqlalchemy import func, select

from backend.core.exceptions import SamProcessingError
from backend.integrations.meta.sam_client import MockSamClient
from backend.models import JobStatus, Observation, ProcessingJob, TrackedObject, Video, VideoStatus
from backend.services.video_ingestion import VideoIngestionService
from backend.services.video_processing import VideoProcessingService

from .conftest import FIXTURE_DIR, MP4_BYTES


class NoopDispatcher:
    async def dispatch_video_processing(self, video_id, job_id) -> None:
        return None


class FailingSam:
    async def process_video(self, video_path, concepts=None, progress=None):
        raise SamProcessingError("boom")


async def _queued(container):
    async with container.session_factory() as session:
        service = VideoIngestionService(session, container.storage, NoopDispatcher(), 10_000)
        video, job = await service.ingest(io.BytesIO(MP4_BYTES), "x.mp4", "video/mp4")
    return video.id, job.id


async def test_success_persists_results_and_completes(container):
    video_id, job_id = await _queued(container)

    async with container.session_factory() as session:
        await VideoProcessingService(
            session, container.storage, container.sam, container.graph
        ).process(video_id, job_id)

    async with container.session_factory() as session:
        video = await session.get(Video, video_id)
        job = await session.get(ProcessingJob, job_id)
        objects = (await session.execute(select(func.count()).select_from(TrackedObject))).scalar()
        observations = (
            await session.execute(select(func.count()).select_from(Observation))
        ).scalar()
    assert video.status == VideoStatus.COMPLETED
    assert video.duration_seconds == pytest.approx(0.133356)
    assert job.status == JobStatus.COMPLETED
    assert job.started_at is not None and job.completed_at is not None
    assert (objects, observations) == (2, 5)
    assert container.graph.calls[0][0] == video_id


async def test_reprocessing_does_not_duplicate_rows(container):
    video_id, job_id = await _queued(container)
    for _ in range(2):
        async with container.session_factory() as session:
            await VideoProcessingService(
                session, container.storage, container.sam, container.graph
            ).process(video_id, job_id)

    async with container.session_factory() as session:
        count = (await session.execute(select(func.count()).select_from(Observation))).scalar()
    assert count == 5


async def test_sam_failure_marks_video_and_job_failed(container):
    video_id, job_id = await _queued(container)

    async with container.session_factory() as session:
        await VideoProcessingService(
            session, container.storage, FailingSam(), container.graph
        ).process(video_id, job_id)

    async with container.session_factory() as session:
        video = await session.get(Video, video_id)
        job = await session.get(ProcessingJob, job_id)
    assert video.status == VideoStatus.FAILED
    assert job.status == JobStatus.FAILED
    assert "boom" in job.error_message
    assert container.graph.calls == []


async def test_failed_job_records_the_failed_stage(container):
    from sqlalchemy import select

    from backend.models import ProcessingJob
    from backend.workers.video_worker import process_video_job

    container.sam = FailingSam()
    video_id, job_id = await _queued(container)
    await process_video_job(container, video_id, job_id)
    async with container.session_factory() as session:
        job = (await session.execute(select(ProcessingJob))).scalar_one()
    assert job.stage == "failed" and job.error_message


async def test_sam_progress_is_recorded_as_stages_while_processing(container):
    from sqlalchemy import select

    from backend.models import ProcessingJob
    from backend.workers.video_worker import process_video_job

    seen = []

    class ReportingSam:
        async def process_video(self, video_path, concepts=None, progress=None):
            await progress("discovering", "Looking")
            await progress("tracking", "1/2 tracked: mug, pen")
            async with container.session_factory() as other:  # a second connection sees it
                seen.append((await other.execute(select(ProcessingJob))).scalar_one().stage)
            return await MockSamClient(FIXTURE_DIR).process_video(video_path)

    container.sam = ReportingSam()
    video_id, job_id = await _queued(container)
    await process_video_job(container, video_id, job_id)
    assert seen == ["tracking"]
    async with container.session_factory() as session:
        assert (await session.execute(select(ProcessingJob))).scalar_one().stage == "completed"
