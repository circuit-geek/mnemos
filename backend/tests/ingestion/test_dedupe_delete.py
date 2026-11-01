import uuid

from sqlalchemy import func, select

from backend.models import Observation, ProcessingJob, TrackedObject, Video, VideoStatus

from .conftest import MP4_BYTES, distinct_mp4


async def _post(client, content, **data):
    return await client.post("/api/v1/videos", data=data,
                             files={"file": ("a.mp4", content, "video/mp4")})


async def _count(container, model):
    async with container.session_factory() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_identical_upload_reuses_the_finished_video(client, container):
    first = await _post(client, MP4_BYTES)
    again = await _post(client, MP4_BYTES)

    assert first.status_code == 202 and first.json()["reused"] is False
    assert again.status_code == 200 and again.json()["reused"] is True
    assert again.json()["video_id"] == first.json()["video_id"]
    assert await _count(container, Video) == 1 and await _count(container, ProcessingJob) == 1


async def test_different_bytes_or_different_concepts_are_new_videos(client, container):
    a = (await _post(client, MP4_BYTES)).json()
    b = (await _post(client, distinct_mp4(1))).json()
    c = (await _post(client, MP4_BYTES, concepts="mug")).json()
    d = (await _post(client, MP4_BYTES, concepts="Mug")).json()  # same concepts after cleaning

    assert len({a["video_id"], b["video_id"], c["video_id"]}) == 3
    assert d["video_id"] == c["video_id"] and d["reused"] is True


async def test_a_failed_video_is_not_reused(client, container):
    first = (await _post(client, MP4_BYTES)).json()
    async with container.session_factory() as session:
        (await session.get(Video, uuid.UUID(first["video_id"]))).status = VideoStatus.FAILED
        await session.commit()
    second = (await _post(client, MP4_BYTES)).json()
    assert second["video_id"] != first["video_id"] and second["reused"] is False


async def test_delete_removes_rows_file_and_graph(client, container):
    graph_calls = []
    container.graph.delete_video_graph = lambda video_id: _record(graph_calls, video_id)
    vid = (await _post(client, MP4_BYTES)).json()["video_id"]
    async with container.session_factory() as session:
        key = (await session.get(Video, uuid.UUID(vid))).storage_key
    assert await _count(container, Observation) > 0

    assert (await client.delete(f"/api/v1/videos/{vid}")).status_code == 204

    for model in (Video, ProcessingJob, TrackedObject, Observation):
        assert await _count(container, model) == 0
    assert graph_calls == [uuid.UUID(vid)]
    assert (await client.get(f"/api/v1/videos/{vid}")).status_code == 404
    assert (await client.get(f"/api/v1/videos/{vid}/media")).status_code == 404
    assert not (container.storage.root / key).exists()


async def _record(calls, video_id):
    calls.append(video_id)


async def test_delete_refuses_while_processing_and_for_unknown_videos(client, container):
    vid = (await _post(client, MP4_BYTES)).json()["video_id"]
    async with container.session_factory() as session:
        (await session.get(Video, uuid.UUID(vid))).status = VideoStatus.PROCESSING
        await session.commit()
    assert (await client.delete(f"/api/v1/videos/{vid}")).status_code == 409
    assert await _count(container, Video) == 1
    assert (await client.delete(f"/api/v1/videos/{uuid.uuid4()}")).status_code == 404
