import pytest

from backend.reasoning.models import Intent, ModelResponseError, QueryIntent
from backend.reasoning.muse_client import MuseClient, parse_json_object
from backend.reasoning.reasoning_service import ReasoningService
from backend.reasoning.retrieval import GraphRetriever

MUG = {"object_id": "o1", "label": "mug", "tracking_id": "0", "first_seen_ms": 0, "last_seen_ms": 18000}


def obs(t, frame):
    return {"observation_id": f"b{frame}", "timestamp_ms": t, "frame_index": frame,
            "bounding_box": [1, 2, 30, 40], "evidence_uri": "raw_response.txt"}


EVENTS = [
    {"event_id": "e1", "object_id": "o1", "event_type": "APPEARED", "start_time_ms": 0,
     "end_time_ms": 0, "description": "mug first detected"},
    {"event_id": "e2", "object_id": "o1", "event_type": "MOVED", "start_time_ms": 0,
     "end_time_ms": 5000, "description": "moved"},
    {"event_id": "e3", "object_id": "o1", "event_type": "NO_LONGER_VISIBLE", "start_time_ms": 10000,
     "end_time_ms": 14000, "description": "missing"},
]


class FakeRepository:
    def __init__(self, objects=(MUG,)):
        self.objects = list(objects)

    def get_video_objects(self, video_id):
        return self.objects

    def get_video_events(self, video_id):
        return EVENTS

    def get_last_observed_position(self, video_id, object_id):
        return obs(18000, 540)

    def get_observation_at_or_before(self, video_id, object_id, timestamp_ms):
        return obs(9000, 270) if timestamp_ms >= 9000 else None


class ScriptedMuse:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def generate_json(self, instructions, payload):
        self.calls.append(payload)
        return self.responses.pop(0)


def service(*responses, objects=(MUG,)):
    muse = ScriptedMuse(*responses)
    return ReasoningService(FakeRepository(objects), muse), muse


def test_parse_json_object_handles_fences_and_rejects_garbage():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ModelResponseError):
        parse_json_object("no json here")
    with pytest.raises(ModelResponseError):
        parse_json_object("[1, 2]")


def test_muse_client_wraps_api_failures():
    class Boom:
        class responses:
            @staticmethod
            def create(**_):
                raise RuntimeError("down")

    with pytest.raises(ModelResponseError):
        MuseClient("k", client=Boom()).generate_json("x", {})


def test_last_seen_retrieves_final_observation_and_visibility_events():
    result = GraphRetriever(FakeRepository()).retrieve(
        "v", QueryIntent(intent=Intent.LAST_SEEN, object_label="mug"))
    kinds = [(e.evidence_id, e.kind) for e in result.evidence]
    assert kinds == [("O1", "object"), ("B1", "observation"), ("E1", "event"), ("E2", "event")]
    assert "NO_LONGER_VISIBLE" in result.evidence[-1].text


def test_changes_filters_to_time_window():
    result = GraphRetriever(FakeRepository()).retrieve(
        "v", QueryIntent(intent=Intent.CHANGES, start_seconds=9, end_seconds=12))
    assert [e.graph_id for e in result.evidence if e.kind == "event"] == ["e3"]


def test_scene_at_time_reports_latest_detection_lag_and_overlapping_events():
    result = GraphRetriever(FakeRepository()).retrieve(
        "v", QueryIntent(intent=Intent.SCENE_AT_TIME, time_seconds=12))
    texts = " ".join(e.text for e in result.evidence)
    assert "3.00s before the requested time" in texts
    assert any(e.graph_id == "e3" for e in result.evidence)


def test_scene_at_time_requires_time_and_unknown_object_is_explicit():
    retriever = GraphRetriever(FakeRepository())
    assert "specific time" in retriever.retrieve("v", QueryIntent(intent=Intent.SCENE_AT_TIME)).problem
    problem = retriever.retrieve("v", QueryIntent(intent=Intent.LAST_SEEN, object_label="laptop")).problem
    assert "laptop" in problem and "mug" in problem


def test_relationships_and_unsupported_never_call_the_model_for_answers():
    svc, muse = service({"intent": "RELATIONSHIPS"})
    answer = svc.ask("v", "is the mug on the desk?")
    assert not answer.sufficient_evidence and "relationships" in answer.answer
    assert len(muse.calls) == 1  # interpretation only


def test_ask_returns_only_valid_cited_evidence():
    svc, muse = service(
        {"intent": "LAST_SEEN", "object_label": "mug"},
        {"answer": "Last detected at 18s.", "evidence_ids": ["B1", "B1", "X99"], "sufficient_evidence": True})
    answer = svc.ask("v", "when did the mug disappear?")
    assert answer.sufficient_evidence
    assert [e.evidence_id for e in answer.evidence] == ["B1"]
    assert muse.calls[0]["known_objects"] == ["mug"]


def test_answer_without_valid_citation_is_withheld():
    svc, _ = service(
        {"intent": "LAST_SEEN", "object_label": "mug"},
        {"answer": "It left.", "evidence_ids": ["X99"], "sufficient_evidence": True})
    answer = svc.ask("v", "where did the mug go?")
    assert not answer.sufficient_evidence and answer.evidence == []


def test_invalid_model_output_raises():
    svc, _ = service({"intent": "NOT_AN_INTENT"})
    with pytest.raises(ModelResponseError):
        svc.ask("v", "?")
