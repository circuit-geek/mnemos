from .conftest import MP4_BYTES


async def _upload(client, name="clip.mp4"):
    return (await client.post("/api/v1/videos",
                              files={"file": (name, MP4_BYTES, "video/mp4")})).json()


async def test_list_returns_newest_first_with_object_counts_and_stage(client):
    first, second = await _upload(client, "a.mp4"), await _upload(client, "b.mp4")

    rows = (await client.get("/api/v1/videos")).json()

    assert [r["id"] for r in rows] == [second["video_id"], first["video_id"]]
    assert rows[0]["object_count"] == 2  # the mock SAM fixture has two tracks
    assert rows[0]["processing_job"]["stage"] == "completed"
    assert rows[0]["width"] == 640 and rows[0]["height"] == 480


async def test_list_respects_limit(client):
    for _ in range(3):
        await _upload(client)
    assert len((await client.get("/api/v1/videos", params={"limit": 2})).json()) == 2
    assert (await client.get("/api/v1/videos", params={"limit": 0})).status_code == 422


async def test_media_streams_the_upload_and_supports_range_requests(client):
    vid = (await _upload(client))["video_id"]

    full = await client.get(f"/api/v1/videos/{vid}/media")
    assert full.status_code == 200 and full.content == MP4_BYTES
    assert full.headers["content-type"] == "video/mp4"

    part = await client.get(f"/api/v1/videos/{vid}/media", headers={"Range": "bytes=4-7"})
    assert part.status_code == 206 and part.content == MP4_BYTES[4:8]


async def test_media_unknown_video_is_404(client):
    import uuid
    assert (await client.get(f"/api/v1/videos/{uuid.uuid4()}/media")).status_code == 404
