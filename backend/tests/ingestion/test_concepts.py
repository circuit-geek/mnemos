import pytest

from backend.core.concepts import parse_concepts
from backend.core.exceptions import InvalidVideoError
from backend.integrations.meta.sam_client import MockSamClient
from backend.models import Video

from .conftest import FIXTURE_DIR, MP4_BYTES


def test_parse_concepts_cleans_dedupes_and_treats_blank_as_none():
    assert parse_concepts(" Mug, notebook ,MUG,,Coffee  Cup ") == ["mug", "notebook", "coffee cup"]
    assert parse_concepts(None) is None
    assert parse_concepts("  , ") is None


@pytest.mark.parametrize("raw", ["--help", "mug; rm -rf /", "x" * 41, "a,b,c,d,e,f,g,h,i", "-mug"])
def test_parse_concepts_rejects_unsafe_or_excessive_input(raw):
    with pytest.raises(InvalidVideoError):
        parse_concepts(raw)


class RecordingSam(MockSamClient):
    def __init__(self, *args):
        super().__init__(*args)
        self.calls = []

    async def process_video(self, video_path, concepts=None, progress=None):
        self.calls.append(concepts)
        result = await super().process_video(video_path, concepts, progress)
        return result.model_copy(update={"concepts": concepts or ["discovered"]})


async def _upload(client, **data):
    return await client.post("/api/v1/videos", data=data,
                             files={"file": ("a.mp4", MP4_BYTES, "video/mp4")})


async def test_upload_concepts_reach_sam_and_are_saved_per_video(client, container):
    container.sam = RecordingSam(FIXTURE_DIR)
    first = (await _upload(client, concepts="Mug, pen")).json()
    second = (await _upload(client)).json()

    assert container.sam.calls == [["mug", "pen"], None]  # second video: discover, no leakage
    one = (await client.get(f"/api/v1/videos/{first['video_id']}")).json()
    two = (await client.get(f"/api/v1/videos/{second['video_id']}")).json()
    assert one["requested_concepts"] == ["mug", "pen"] and one["tracked_concepts"] == ["mug", "pen"]
    assert two["requested_concepts"] is None and two["tracked_concepts"] == ["discovered"]


async def test_invalid_concepts_are_rejected_before_anything_is_stored(client, container):
    response = await _upload(client, concepts="--help")
    assert response.status_code == 400
    async with container.session_factory() as session:
        from sqlalchemy import select
        assert (await session.execute(select(Video))).first() is None
