import uuid

from sqlalchemy import select

from backend.models import JobStatus, ProcessingJob, Video, VideoStatus

from .conftest import MP4_BYTES


async def _upload(client, content=MP4_BYTES, content_type="video/mp4", name="clip.mp4"):
    return await client.post("/api/v1/videos", files={"file": (name, content, content_type)})


async def test_upload_returns_202_and_creates_records(client, container):
    response = await _upload(client)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    async with container.session_factory() as session:
        video = await session.get(Video, uuid.UUID(body["video_id"]))
        job = await session.get(ProcessingJob, uuid.UUID(body["job_id"]))
    assert video.original_filename == "clip.mp4"
    assert video.size_bytes == len(MP4_BYTES)
    assert job.video_id == video.id
    stored = await container.storage.get_download_reference(video.storage_key)
    assert open(stored, "rb").read() == MP4_BYTES


async def test_upload_triggers_processing_to_completion(client, container):
    body = (await _upload(client)).json()

    # ASGI transport runs background tasks before returning.
    detail = (await client.get(f"/api/v1/videos/{body['video_id']}")).json()
    assert detail["status"] == "completed"
    assert detail["processing_job"]["id"] == body["job_id"]
    assert detail["processing_job"]["status"] == "completed"
    assert len(container.graph.calls) == 1


async def test_observations_endpoint_returns_processed_rows(client):
    body = (await _upload(client)).json()

    rows = (await client.get(f"/api/v1/videos/{body['video_id']}/observations")).json()
    assert len(rows) == 5
    assert rows[0]["label"] == "mug"
    assert rows[0]["bbox"] == [100, 100, 200, 200]
    assert rows[0]["tracked_object_id"] is not None


async def test_rejects_unsupported_content_type(client, container):
    response = await _upload(client, b"hello", "text/plain", "a.txt")

    assert response.status_code == 415
    async with container.session_factory() as session:
        assert (await session.execute(select(Video))).first() is None


async def test_rejects_spoofed_and_empty_uploads(client):
    assert (await _upload(client, b"not a video at all")).status_code == 400
    assert (await _upload(client, b"")).status_code == 400


async def test_unknown_video_is_404(client):
    assert (await client.get(f"/api/v1/videos/{uuid.uuid4()}")).status_code == 404
    assert (await client.get(f"/api/v1/videos/{uuid.uuid4()}/observations")).status_code == 404


async def test_status_is_queued_before_processing(client, container):
    # Bypass dispatch by creating the rows through the ingestion service with a no-op dispatcher.
    from backend.services.video_ingestion import VideoIngestionService

    class NoopDispatcher:
        async def dispatch_video_processing(self, video_id, job_id) -> None:
            return None

    import io

    async with container.session_factory() as session:
        service = VideoIngestionService(session, container.storage, NoopDispatcher(), 10_000)
        video, job = await service.ingest(io.BytesIO(MP4_BYTES), "x.mp4", "video/mp4")

    detail = (await client.get(f"/api/v1/videos/{video.id}")).json()
    assert detail["status"] == VideoStatus.QUEUED
    assert detail["processing_job"]["status"] == JobStatus.PENDING
