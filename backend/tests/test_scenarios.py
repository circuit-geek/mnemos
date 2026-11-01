"""Replays real recorded runs (fixtures/scenarios, made by scripts/record_scenario_fixtures.py).

Muse Spark's interpretations and answers were recorded from live runs; here the interpretation is
fed through the real retrieval code against the recorded memory. No model is called.
"""

import bisect
import json
from pathlib import Path

import pytest

from backend.reasoning.models import Intent, QueryIntent
from backend.reasoning.retrieval import GraphRetriever

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios"
NAMES = ["scenario_1", "scenario_2", "scenario_3"]


class FixtureRepository:
    """Serves a recorded memory through the same methods as the Neo4j repository."""

    def __init__(self, data):
        self.objects = data["objects"]
        self.events = data["events"]
        self.relationships = data["relationships"]
        self.by_object: dict[str, list[dict]] = {o["object_id"]: [] for o in self.objects}
        for index, ts, frame, left, top, right, bottom in data["observations"]:
            object_id = self.objects[index]["object_id"]
            self.by_object[object_id].append({
                "observation_id": f"{object_id}:{frame}", "timestamp_ms": ts, "frame_index": frame,
                "bounding_box": [left, top, right, bottom], "evidence_uri": None})
        for rows in self.by_object.values():
            rows.sort(key=lambda r: r["timestamp_ms"])

    def get_video_objects(self, video_id):
        return self.objects

    def get_video_events(self, video_id):
        return self.events

    def get_video_relationships(self, video_id):
        return self.relationships

    def get_last_observed_position(self, video_id, object_id):
        rows = self.by_object[object_id]
        return rows[-1] if rows else None

    def get_observation_at_or_before(self, video_id, object_id, timestamp_ms):
        rows = self.by_object[object_id]
        i = bisect.bisect_right([r["timestamp_ms"] for r in rows], timestamp_ms)
        return rows[i - 1] if i else None


def load(name):
    return json.loads((FIXTURE_DIR / f"{name}.json").read_text())


CASES = [(name, case) for name in NAMES for case in load(name)["cases"]]


@pytest.mark.parametrize("name,case", CASES, ids=[f"{n}:{c['question'][:40]}" for n, c in CASES])
def test_every_recorded_answer_is_backed_by_evidence_that_retrieval_reproduces(name, case):
    repo = FixtureRepository(load(name))
    intent = QueryIntent.model_validate(case["intent"])

    result = GraphRetriever(repo).retrieve("v", intent)

    if intent.intent is Intent.UNSUPPORTED or not case["sufficient_evidence"]:
        assert result.problem or not case["cited"]
        return
    assert result.problem is None, result.problem
    retrieved = {e.text for e in result.evidence}
    missing = [text for text in case["cited"] if text not in retrieved]
    assert not missing, f"cited evidence no longer produced: {missing}"


@pytest.mark.parametrize("name", NAMES)
def test_recorded_memory_is_internally_consistent(name):
    data = load(name)
    ids = {o["object_id"] for o in data["objects"]}
    for event in data["events"]:
        assert event["object_id"] in ids and event["end_time_ms"] >= event["start_time_ms"]
    for rel in data["relationships"]:
        assert {rel["subject_object_id"], rel["target_object_id"]} <= ids
        assert rel["valid_to_ms"] is None or rel["valid_to_ms"] > rel["valid_from_ms"]


@pytest.mark.parametrize("name", NAMES)
def test_proximity_between_a_pair_never_overlaps_or_flickers(name):
    """NEAR/NEXT_TO between one pair is a single continuous interval, not interleaved flips."""
    spans: dict[frozenset, list[tuple[int, float]]] = {}
    for rel in load(name)["relationships"]:
        if rel["relation_type"] in ("NEAR", "NEXT_TO"):
            pair = frozenset((rel["subject_object_id"], rel["target_object_id"]))
            spans.setdefault(pair, []).append(
                (rel["valid_from_ms"], float("inf") if rel["valid_to_ms"] is None else rel["valid_to_ms"]))
    for pair_spans in spans.values():
        pair_spans.sort()
        for (_, end), (start, _) in zip(pair_spans, pair_spans[1:], strict=False):
            assert start >= end


@pytest.mark.parametrize("name", NAMES)
def test_movement_is_a_few_segments_not_a_stream_of_events(name):
    moved = [e for e in load(name)["events"] if e["event_type"] == "MOVED"]
    objects = len(load(name)["objects"])
    assert len(moved) <= objects * 3


def test_scenario_1_mug_that_left_and_returned_is_one_object_with_a_gap():
    data = load("scenario_1")
    assert sorted(o["label"] for o in data["objects"]) == ["laptop", "mug"]
    [mug] = [o for o in data["objects"] if o["label"] == "mug"]
    assert mug["last_seen_ms"] > 20000  # tracked through the end, not just the first 9.7 s
    [gap] = [e for e in data["events"] if e["event_type"] == "NO_LONGER_VISIBLE"]
    assert 9500 <= gap["start_time_ms"] <= 10000 and 15000 <= gap["end_time_ms"] <= 15500


def test_scenario_2_objects_appear_when_they_do_in_the_video():
    first = {o["label"]: o["first_seen_ms"] for o in load("scenario_2")["objects"]}
    assert first["mug"] == 0 and first["pen"] == 0
    assert 7800 <= first["notebook"] <= 8200 and 15400 <= first["phone"] <= 15900


def test_scenario_3_mug_ends_up_on_the_notebook():
    data = load("scenario_3")
    labels = {o["object_id"]: o["label"] for o in data["objects"]}
    on = [(labels[r["subject_object_id"]], labels[r["target_object_id"]], r["valid_from_ms"])
          for r in data["relationships"] if r["relation_type"] == "ON"]
    assert [(a, b) for a, b, _ in on] == [("mug", "notebook")] and on[0][2] >= 18000


def test_before_the_notebook_appeared_lists_pen_and_mug_but_not_the_notebook():
    repo = FixtureRepository(load("scenario_2"))
    result = GraphRetriever(repo).retrieve("v", QueryIntent(intent=Intent.SCENE_AT_TIME, before_appearance_of="notebook"))
    kinds = " ".join(e.text for e in result.evidence if e.kind == "object")
    assert "'pen'" in kinds and "'mug'" in kinds and "'notebook'" not in kinds
