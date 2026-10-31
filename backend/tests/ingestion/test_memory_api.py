import uuid
import uuid

import pytest

from backend.reasoning.models import Answer, Intent, ModelResponseError, QueryIntent

OBJ = {"object_id": "o1", "tracking_id": "1", "label": "mug", "first_seen_ms": 0, "last_seen_ms": 5000}
LATE = {**OBJ, "object_id": "o2", "tracking_id": "2", "first_seen_ms": 4000}
OBS = {"observation_id": "b1", "timestamp_ms": 0, "frame_index": 0, "bounding_box": [1, 2, 3, 4],
       "confidence": 0.9, "evidence_uri": None}
EVENTS = [
    {"event_id": "e1", "object_id": "o1", "event_type": "APPEARED", "start_time_ms": 0,
     "end_time_ms": 0, "description": "mug first detected", "confidence": None},
    {"event_id": "e2", "object_id": "o2", "event_type": "APPEARED", "start_time_ms": 4000,
     "end_time_ms": 4000, "description": "mug first detected", "confidence": None},
]


REL = {"relationship_id": "r1", "subject_object_id": "o1", "target_object_id": "o2",
       "relation_type": "NEXT_TO", "valid_from_ms": 4000, "valid_to_ms": 9000,
       "last_verified_ms": 8000, "evidence_timestamp_ms": 4000, "confidence": 0.9,
       "reason": "side by side"}


class FakeMemory:
    def get_video_relationships(self, video_id):
        return [REL]

    def get_video_observations(self, video_id):
        return [{**OBS, "object_id": "o1"}, {**OBS, "observation_id": "b2", "timestamp_ms": 500,
                                              "object_id": "o2"}]

    def get_video_objects(self, video_id):
        return [OBJ, LATE]

    def get_video_events(self, video_id):
        return EVENTS

    def get_object_history(self, video_id, object_id):
        return [OBS]

    def get_observation_at_or_before(self, video_id, object_id, timestamp_ms):
        return OBS


class FakeReasoning:
    def __init__(self, error=None):
        self.error = error

    def ask(self, video_id, question):
        if self.error:
            raise self.error
        return Answer(question=question, intent=QueryIntent(intent=Intent.CHANGES),
                      answer="a mug appeared", sufficient_evidence=True, evidence=[])


async def _video_id(client, mp4_file):
    response = await client.post("/api/v1/videos", files={"file": ("a.mp4", mp4_file, "video/mp4")})
    return response.json()["video_id"]


@pytest.fixture
def with_memory(container):
    container.memory = FakeMemory()
    container.reasoning = FakeReasoning()
    return container


async def test_ask_returns_answer(client, mp4_file, with_memory):
    vid = await _video_id(client, mp4_file)
    r = await client.post(f"/api/v1/videos/{vid}/ask", json={"question": "what changed?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "a mug appeared"


async def test_ask_unknown_video_is_404(client, with_memory):
    r = await client.post(f"/api/v1/videos/{uuid.uuid4()}/ask", json={"question": "hi"})
    assert r.status_code == 404


async def test_ask_rejects_empty_question(client, mp4_file, with_memory):
    vid = await _video_id(client, mp4_file)
    r = await client.post(f"/api/v1/videos/{vid}/ask", json={"question": ""})
    assert r.status_code == 422


async def test_ask_model_failure_is_502(client, mp4_file, with_memory):
    with_memory.reasoning = FakeReasoning(ModelResponseError("boom"))
    vid = await _video_id(client, mp4_file)
    r = await client.post(f"/api/v1/videos/{vid}/ask", json={"question": "hi"})
    assert r.status_code == 502


async def test_memory_disabled_is_503(client, mp4_file):
    vid = await _video_id(client, mp4_file)
    assert (await client.get(f"/api/v1/videos/{vid}/events")).status_code == 503


async def test_reasoning_not_configured_is_503(client, mp4_file, container):
    container.memory = FakeMemory()
    vid = await _video_id(client, mp4_file)
    r = await client.post(f"/api/v1/videos/{vid}/ask", json={"question": "hi"})
    assert r.status_code == 503


async def test_objects_events_history(client, mp4_file, with_memory):
    vid = await _video_id(client, mp4_file)
    assert len((await client.get(f"/api/v1/videos/{vid}/objects")).json()) == 2
    assert len((await client.get(f"/api/v1/videos/{vid}/events")).json()) == 2
    history = await client.get(f"/api/v1/videos/{vid}/objects/o1/history")
    assert history.json()[0]["observation_id"] == "b1"


async def test_graph_snapshot_respects_time(client, mp4_file, with_memory):
    vid = await _video_id(client, mp4_file)
    full = (await client.get(f"/api/v1/videos/{vid}/graph")).json()
    assert {n["id"] for n in full["nodes"]} == {vid, "o1", "o2", "e1", "e2"}
    assert any(e["type"] == "NEXT_TO" and e["id"] == "r1" for e in full["edges"])
    early = (await client.get(f"/api/v1/videos/{vid}/graph", params={"at_seconds": 1})).json()
    assert {n["id"] for n in early["nodes"]} == {vid, "o1", "e1"}
    assert early["at_ms"] == 1000
    assert not any(e["type"] == "NEXT_TO" for e in early["edges"])
    assert all(e["source"] in {n["id"] for n in early["nodes"]} for e in early["edges"])


def _real_clip(path):
    import subprocess

    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10",
         "-t", "2", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )
    return path.read_bytes()


async def test_frame_endpoint_returns_jpeg(client, tmp_path):
    data = _real_clip(tmp_path / "clip.mp4")
    r = await client.post("/api/v1/videos", files={"file": ("a.mp4", data, "video/mp4")})
    vid = r.json()["video_id"]
    frame = await client.get(f"/api/v1/videos/{vid}/frames/500")
    assert frame.status_code == 200
    assert frame.headers["content-type"] == "image/jpeg"
    assert frame.content[:2] == b"\xff\xd8"


async def test_frame_endpoint_rejects_bad_input(client, mp4_file):
    assert (await client.get(f"/api/v1/videos/{uuid.uuid4()}/frames/0")).status_code == 404
    vid = await _video_id(client, mp4_file)
    assert (await client.get(f"/api/v1/videos/{vid}/frames/-1")).status_code == 422
    assert (await client.get(f"/api/v1/videos/{vid}/frames/abc")).status_code == 422


async def test_evidence_uris_are_frame_urls_not_local_paths(client, mp4_file, with_memory):
    from backend.reasoning.models import Evidence

    evidence = [Evidence(evidence_id="B1", kind="observation", timestamp_ms=1200, text="x",
                         evidence_uri="file:///home/user/secret/raw_response.txt#frame=3"),
                Evidence(evidence_id="O1", kind="object", text="y")]
    base = with_memory.reasoning.ask
    with_memory.reasoning.ask = lambda v, q: base(v, q).model_copy(update={"evidence": evidence})
    vid = await _video_id(client, mp4_file)

    body = (await client.post(f"/api/v1/videos/{vid}/ask", json={"question": "q"})).json()
    assert body["evidence"][0]["evidence_uri"] == f"/api/v1/videos/{vid}/frames/1200"
    assert body["evidence"][1]["evidence_uri"] is None
    history = (await client.get(f"/api/v1/videos/{vid}/objects/o1/history")).json()
    assert history[0]["evidence_uri"] == f"/api/v1/videos/{vid}/frames/0"
    assert "file://" not in str(body) + str(history)


async def test_relationships_endpoint_filters_by_time_and_object(client, mp4_file, with_memory):
    vid = await _video_id(client, mp4_file)
    base = f"/api/v1/videos/{vid}/relationships"
    rows = (await client.get(base)).json()
    assert rows[0]["relation_type"] == "NEXT_TO"
    assert rows[0]["evidence_uri"] == f"/api/v1/videos/{vid}/frames/4000"
    assert len((await client.get(base, params={"at_seconds": 5})).json()) == 1
    assert (await client.get(base, params={"at_seconds": 9})).json() == []  # end is exclusive
    assert (await client.get(base, params={"at_seconds": 1})).json() == []
    assert len((await client.get(base, params={"object_id": "o2"})).json()) == 1
    assert (await client.get(base, params={"object_id": "zzz"})).json() == []


async def test_memory_bundle_has_full_history_and_derived_relationship_events(
    client, mp4_file, with_memory
):
    vid = await _video_id(client, mp4_file)
    bundle = (await client.get(f"/api/v1/videos/{vid}/memory")).json()
    assert {o["object_id"] for o in bundle["objects"]} == {"o1", "o2"}
    assert [(o["object_id"], o["timestamp_ms"]) for o in bundle["observations"]] == [
        ("o1", 0), ("o2", 500)]
    assert bundle["observations"][1]["evidence_uri"] == f"/api/v1/videos/{vid}/frames/500"
    kinds = [(e["event_type"], e["start_time_ms"]) for e in bundle["events"]]
    assert ("RELATIONSHIP_STARTED", 4000) in kinds and ("RELATIONSHIP_ENDED", 9000) in kinds
    started = next(e for e in bundle["events"] if e["event_type"] == "RELATIONSHIP_STARTED")
    assert started["relationship_id"] == "r1" and started["related_object_id"] == "o2"
    assert started["description"] == "mug NEXT_TO mug began"
    assert [e["start_time_ms"] for e in bundle["events"]] == sorted(
        e["start_time_ms"] for e in bundle["events"])
