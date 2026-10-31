import asyncio
from pathlib import Path

import pytest

from backend.integrations.meta import concept_discovery
from backend.integrations.meta.concept_discovery import ConceptDiscoverer
from backend.integrations.meta.sam_client import ScriptSamClient
from backend.integrations.meta.sam_models import (
    ObservationResult,
    TrackedObjectResult,
    VideoProcessingResult,
)


def clean(*names):
    return ConceptDiscoverer.clean({"objects": [{"name": n} if isinstance(n, str) else n
                                                for n in names]})


def test_clean_normalises_dedupes_and_drops_surfaces_and_body_parts():
    assert clean("Mug", " mug ", "Notebook", "table", "Hand", "desk", "pen") == [
        "mug", "notebook", "pen"]


def test_clean_drops_malformed_and_overlong_entries():
    assert clean({"name": 5}, {"label": "mug"}, "x" * 50, "a very long object name", "", "phone",
                 "junk") == ["phone", "junk"]
    assert ConceptDiscoverer.clean({"objects": "mug"}) == []
    assert ConceptDiscoverer.clean({}) == []


class ScriptedMuse:
    def __init__(self, raw):
        self.raw, self.calls = raw, []

    def generate_json(self, instructions, payload, images=None):
        self.calls.append((payload, images))
        return self.raw


@pytest.fixture
def media(monkeypatch):
    requested = []

    async def duration(path):
        return 20000

    async def frame(path, timestamp_ms, max_width=None):
        requested.append(timestamp_ms)
        return f"frame{timestamp_ms}".encode()

    monkeypatch.setattr(concept_discovery, "probe_duration_ms", duration)
    monkeypatch.setattr(concept_discovery, "extract_frame_jpeg", frame)
    return requested


def test_discover_samples_frames_across_the_whole_video_in_one_model_call(media):
    muse = ScriptedMuse({"objects": [{"name": "mug"}, {"name": "pen"}]})
    found = asyncio.run(ConceptDiscoverer(muse, frames=4).discover(Path("v.mp4")))
    assert found == ["mug", "pen"]
    assert media == [2500, 7500, 12500, 17500]  # midpoints of four equal slices
    [(payload, images)] = muse.calls
    assert len(images) == 4 and payload["frame_times_seconds"] == [2.5, 7.5, 12.5, 17.5]


def test_discover_caps_the_number_of_concepts(media):
    muse = ScriptedMuse({"objects": [{"name": n} for n in "abcdefgh"]})
    assert len(asyncio.run(ConceptDiscoverer(muse, max_concepts=3).discover(Path("v.mp4")))) == 3


# --- SAM client chooses concepts ---------------------------------------------------------------

def sam(label):
    return VideoProcessingResult(
        duration_seconds=1, width=10, height=10,
        objects=[TrackedObjectResult(tracking_id="0", label=label, first_seen_seconds=0,
                                     last_seen_seconds=1)],
        observations=[ObservationResult(tracking_id="0", label=label, timestamp_seconds=0,
                                        frame_number=0, bbox=[1, 1, 5, 5])])


class FakeDiscoverer:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    async def discover(self, path):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def client(monkeypatch, discoverer=None, **kwargs):
    ran = []
    instance = ScriptSamClient(Path("s.py"), "key", discoverer or FakeDiscoverer(["unused"]), **kwargs)

    async def run(video_path, concept):
        ran.append(concept)
        return sam(concept)

    monkeypatch.setattr(instance, "_run_script", run)
    return instance, ran


def test_discovered_concepts_are_each_tracked_and_merged(monkeypatch):
    sam_client, ran = client(monkeypatch, discoverer=FakeDiscoverer(["mug", "pen"]))
    result = asyncio.run(sam_client.process_video(Path("v.mp4")))
    assert sorted(ran) == ["mug", "pen"]
    assert sorted(o.tracking_id for o in result.objects) == ["mug-0", "pen-0"]
    assert result.concepts == ["mug", "pen"]


def test_requested_concepts_for_this_video_override_discovery(monkeypatch):
    discoverer = FakeDiscoverer(["ignored"])
    sam_client, ran = client(monkeypatch, discoverer=discoverer)
    result = asyncio.run(sam_client.process_video(Path("v.mp4"), ["laptop"]))
    assert ran == ["laptop"] and discoverer.calls == 0 and result.concepts == ["laptop"]


def test_each_video_gets_its_own_concepts(monkeypatch):
    sam_client, ran = client(monkeypatch, discoverer=FakeDiscoverer(["mug"]))
    asyncio.run(sam_client.process_video(Path("a.mp4"), ["pen"]))
    asyncio.run(sam_client.process_video(Path("b.mp4")))
    assert ran == ["pen", "mug"]  # nothing leaks from one video to the next


@pytest.mark.parametrize("discoverer", [FakeDiscoverer([]), FakeDiscoverer(error=RuntimeError("x"))])
def test_falls_back_to_the_generic_concept_when_discovery_finds_nothing(monkeypatch, discoverer):
    sam_client, ran = client(monkeypatch, discoverer=discoverer, fallback_concept="object")
    asyncio.run(sam_client.process_video(Path("v.mp4")))
    assert ran == ["object"]

