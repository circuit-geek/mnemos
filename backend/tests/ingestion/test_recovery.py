

from backend.core.exceptions import SamProcessingError
from backend.integrations.meta.sam_client import ScriptSamClient
from backend.models import JobStatus, ProcessingJob, Video, VideoStatus
from backend.services.recovery import MESSAGE, fail_interrupted_jobs

from .test_video_processing import NoopDispatcher, _queued  # noqa: F401


async def test_unfinished_work_is_failed_with_a_clear_reason_and_finished_work_is_kept(container):
    stuck_video, stuck_job = await _queued(container)
    done_video, done_job = await _queued(container)
    async with container.session_factory() as session:
        (await session.get(Video, done_video)).status = VideoStatus.COMPLETED
        (await session.get(ProcessingJob, done_job)).status = JobStatus.COMPLETED
        (await session.get(ProcessingJob, stuck_job)).status = JobStatus.RUNNING
        (await session.get(Video, stuck_video)).status = VideoStatus.PROCESSING
        await session.commit()

    assert await fail_interrupted_jobs(container.session_factory) == 1

    async with container.session_factory() as session:
        video = await session.get(Video, stuck_video)
        job = await session.get(ProcessingJob, stuck_job)
        assert video.status == VideoStatus.FAILED
        assert job.status == JobStatus.FAILED and job.stage == "failed" and job.error_message == MESSAGE
        assert (await session.get(Video, done_video)).status == VideoStatus.COMPLETED
        assert (await session.get(ProcessingJob, done_job)).status == JobStatus.COMPLETED


async def test_a_hung_sam_run_times_out_instead_of_blocking_forever(tmp_path):
    script = tmp_path / "hang.py"
    script.write_text("import time\ntime.sleep(60)\n")
    client = ScriptSamClient(script, "key", discoverer=None, timeout_seconds=0.5)
    try:
        await client._run_script(tmp_path / "v.mp4", "mug")
    except SamProcessingError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("expected a timeout")
