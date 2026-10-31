import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.integrations.meta.sam_client import merge_results
from backend.integrations.meta.sam_models import (
    ObservationResult,
    TrackedObjectResult,
    VideoProcessingResult,
)
from backend.integrations.neo4j.graph_writer import build_memory_batch
from backend.memory.models import SPATIAL_RELATION_TYPES
from backend.memory.repository import CREATE_RELATIONSHIP
from backend.reasoning.models import Intent, QueryIntent
from backend.reasoning.retrieval import GraphRetriever
from backend.scene import scene_service
from backend.scene.intervals import Detected, Sample, build_relationships
from backend.scene.scene_service import SceneAnalyzer

from test_reasoning import FakeRepository

V = "video-1"


def detected(kind="NEXT_TO", a="A", b="B", confidence=0.9):
    return Detected(kind, a, b, confidence, "reason")


# --- interval building -------------------------------------------------------------------------

def test_relation_opens_at_first_detection_and_closes_when_no_longer_reported():
    samples = [
        Sample(0, frozenset("AB")),
        Sample(2000, frozenset("AB"), [detected()]),
        Sample(4000, frozenset("AB"), [detected()]),
        Sample(6000, frozenset("AB")),
    ]
    [rel] = build_relationships(V, samples)
    assert (rel.valid_from_ms, rel.valid_to_ms, rel.last_verified_ms) == (2000, 6000, 4000)
    assert rel.evidence_timestamp_ms == 2000


def test_relation_still_holding_at_the_end_stays_open():
    [rel] = build_relationships(V, [Sample(0, frozenset("AB"), [detected()]),
                                    Sample(2000, frozenset("AB"), [detected()])])
    assert rel.valid_to_ms is None and rel.last_verified_ms == 2000


def test_visibility_gap_does_not_end_a_relation():
    samples = [
        Sample(0, frozenset("AB"), [detected("ON")]),
        Sample(2000, frozenset("A")),  # B hidden: no evidence the relation ended
        Sample(4000, frozenset("AB"), [detected("ON")]),
    ]
    [rel] = build_relationships(V, samples)
    assert rel.valid_from_ms == 0 and rel.valid_to_ms is None


def test_failed_sample_is_neutral():
    samples = [Sample(0, frozenset("AB"), [detected()]),
               Sample(2000, frozenset("AB"), verified=False),
               Sample(4000, frozenset("AB"), [detected()])]
    [rel] = build_relationships(V, samples)
    assert rel.valid_to_ms is None


def test_relation_can_reopen_as_a_new_interval_with_distinct_ids():
    samples = [Sample(0, frozenset("AB"), [detected()]), Sample(2000, frozenset("AB")),
               Sample(4000, frozenset("AB"), [detected()])]
    first, second = build_relationships(V, samples)
    assert (first.valid_from_ms, first.valid_to_ms) == (0, 2000)
    assert second.valid_from_ms == 4000 and second.valid_to_ms is None
    assert first.relationship_id != second.relationship_id


def test_symmetric_relations_are_one_relation_either_way_round():
    samples = [Sample(0, frozenset("AB"), [detected(a="A", b="B")]),
               Sample(2000, frozenset("AB"), [detected(a="B", b="A")])]
    [rel] = build_relationships(V, samples)
    assert rel.valid_to_ms is None


def test_on_is_directional():
    samples = [Sample(0, frozenset("AB"), [detected("ON", "A", "B")]),
               Sample(2000, frozenset("AB"), [detected("ON", "B", "A")])]
    assert len(build_relationships(V, samples)) == 2


def test_relationship_ids_are_stable():
    samples = [Sample(0, frozenset("AB"), [detected()])]
    assert build_relationships(V, samples) == build_relationships(V, samples)


# --- scene analyzer ----------------------------------------------------------------------------

def result():
    def obs(tid, label, ts, frame):
        return ObservationResult(tracking_id=tid, label=label, timestamp_seconds=ts,
                                 frame_number=frame, bbox=[10, 10, 50, 50])
    return VideoProcessingResult(
        duration_seconds=6.0, width=100, height=100,
        objects=[TrackedObjectResult(tracking_id="mug-0", label="mug", first_seen_seconds=0,
                                     last_seen_seconds=6),
                 TrackedObjectResult(tracking_id="book-0", label="book", first_seen_seconds=0,
                                     last_seen_seconds=6)],
        observations=[obs(tid, label, t, t * 10)
                      for t in (0, 2, 4, 6)
                      for tid, label in (("mug-0", "mug"), ("book-0", "book"))])


class ScriptedScene:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def generate_json(self, instructions, payload, images=None):
        assert images
        self.calls.append(payload)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def no_ffmpeg(monkeypatch):
    async def fake(path, timestamp_ms, max_width=None):
        return b"jpeg"
    monkeypatch.setattr(scene_service, "extract_frame_jpeg", fake)


def analyze(muse, **kwargs):
    batch = build_memory_batch("11111111-1111-1111-1111-111111111111", "c.mp4",
                               datetime.now(UTC), result())
    analyzer = SceneAnalyzer(muse, interval_ms=2000, **kwargs)
    return batch, asyncio.run(analyzer.analyze(Path("x.mp4"), batch, (100, 100)))


def rel(subject, relation, obj, confidence=0.9):
    return {"subject": subject, "relation": relation, "object": obj, "confidence": confidence,
            "reason": "seen"}


def test_analyzer_builds_validated_intervals_from_model_output():
    on = {"relationships": [rel("mug_1", "ON", "book_1")]}
    none = {"relationships": []}
    muse = ScriptedScene(on, on, none, none)
    batch, relationships = analyze(muse)
    [r] = relationships
    names = {o.object_id: o.label for o in batch.objects}
    assert (names[r.subject_object_id], r.relation_type, names[r.target_object_id]) == (
        "mug", "ON", "book")
    assert (r.valid_from_ms, r.valid_to_ms) == (0, 4000)
    first = muse.calls[0]
    assert {o["id"] for o in first["objects"]} == {"mug_1", "book_1"}
    assert first["objects"][0]["box"] == [0.1, 0.1, 0.5, 0.5]  # normalised, not raw pixels


def test_analyzer_drops_unknown_ids_low_confidence_and_malformed_entries():
    noisy = {"relationships": [rel("mug_1", "ON", "ghost_9"), rel("mug_1", "ON", "mug_1"),
                               rel("mug_1", "NEAR", "book_1", confidence=0.3),
                               {"subject": "mug_1"}, "junk", rel("mug_1", "FLOATS", "book_1")]}
    _, relationships = analyze(ScriptedScene(*[noisy] * 4))
    assert relationships == []


def test_contains_is_stored_once_as_inverse_inside():
    out = {"relationships": [rel("book_1", "CONTAINS", "mug_1")]}
    batch, [r] = analyze(ScriptedScene(*[out] * 4))
    names = {o.object_id: o.label for o in batch.objects}
    assert (names[r.subject_object_id], r.relation_type, names[r.target_object_id]) == (
        "mug", "INSIDE", "book")


def test_model_failure_skips_the_sample_without_closing_relations():
    from backend.reasoning.models import ModelResponseError
    on = {"relationships": [rel("mug_1", "NEXT_TO", "book_1")]}
    _, [r] = analyze(ScriptedScene(on, ModelResponseError("boom"), on, on))
    assert r.valid_to_ms is None


def test_samples_need_two_visible_objects():
    muse = ScriptedScene()
    single = VideoProcessingResult(
        duration_seconds=4, width=100, height=100,
        objects=[TrackedObjectResult(tracking_id="0", label="mug", first_seen_seconds=0,
                                     last_seen_seconds=4)],
        observations=[ObservationResult(tracking_id="0", label="mug", timestamp_seconds=0,
                                        frame_number=0, bbox=[1, 1, 5, 5])])
    batch = build_memory_batch("11111111-1111-1111-1111-111111111111", "c.mp4",
                               datetime.now(UTC), single)
    assert asyncio.run(SceneAnalyzer(muse).analyze(Path("x.mp4"), batch)) == []
    assert muse.calls == []


# --- retrieval ---------------------------------------------------------------------------------

MUG = {"object_id": "o1", "label": "mug", "tracking_id": "m", "first_seen_ms": 0, "last_seen_ms": 18000}
BOOK = {"object_id": "o2", "label": "book", "tracking_id": "b", "first_seen_ms": 8000, "last_seen_ms": 18000}
PEN = {"object_id": "o3", "label": "pen", "tracking_id": "p", "first_seen_ms": 0, "last_seen_ms": 18000}


def stored(rid, subject, kind, target, start, end):
    return {"relationship_id": rid, "subject_object_id": subject, "target_object_id": target,
            "relation_type": kind, "valid_from_ms": start, "valid_to_ms": end,
            "last_verified_ms": (end or 18000), "evidence_timestamp_ms": start, "confidence": 0.9,
            "reason": "seen"}


RELS = [stored("r1", "o1", "NEXT_TO", "o3", 0, 8000), stored("r2", "o1", "ON", "o2", 10000, None)]


def retrieve(intent, rels=RELS):
    repo = FakeRepository(objects=(MUG, BOOK, PEN), relationships=rels)
    return GraphRetriever(repo).retrieve("v", intent)


def ids(result):
    return [e.evidence_id for e in result.evidence if e.kind == "relationship"]


def test_relationships_at_a_time_respect_half_open_intervals():
    at = lambda s: retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, object_label="mug", time_seconds=s))
    assert ids(at(5)) == ["R1"]
    assert at(8).problem  # r1 ended at 8s (exclusive); r2 not started
    assert ids(at(12)) == ["R1"]  # r2 is the first matching relation here


def test_relationship_filters_by_type_and_anchor_object():
    result = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, object_label="mug", relation_type="ON"))
    assert [e.graph_id for e in result.evidence] == ["r2"]
    assert "'mug' ON 'book'" in result.evidence[0].text and "still holding" in result.evidence[0].text
    other = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, object_label="pen"))
    assert [e.graph_id for e in other.evidence] == ["r1"]  # object may be the target side


def test_before_appearance_resolves_the_moment_and_lists_objects_present_then():
    result = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, before_appearance_of="book"))
    assert [e.graph_id for e in result.evidence if e.kind == "relationship"] == ["r1"]
    assert sorted(e.graph_id for e in result.evidence if e.kind == "object") == ["o1", "o3"]


def test_window_overlap():
    window = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, start_seconds=8, end_seconds=9))
    assert window.problem  # r1 ended at 8s, r2 starts at 10s


def test_no_relationships_stored_is_explicit():
    result = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS), rels=[])
    assert result.problem and "No spatial relationships" in result.problem


def test_unknown_before_object_is_explicit():
    result = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, before_appearance_of="laptop"))
    assert "laptop" in result.problem


def test_scene_at_time_includes_relations_and_excludes_objects_not_yet_seen():
    result = retrieve(QueryIntent(intent=Intent.SCENE_AT_TIME, before_appearance_of="book"))
    assert "o2" not in [e.graph_id for e in result.evidence]
    assert "r1" in [e.graph_id for e in result.evidence]


def test_query_intent_normalises_relation_words():
    assert QueryIntent(intent=Intent.RELATIONSHIPS, relation_type="contains").relation_type == "INSIDE"
    assert QueryIntent(intent=Intent.RELATIONSHIPS, relation_type="next to").relation_type == "NEXT_TO"
    assert QueryIntent(intent=Intent.RELATIONSHIPS, relation_type="levitating").relation_type is None


# --- SAM merge and storage templates -----------------------------------------------------------

def sam(label, tid="0"):
    return VideoProcessingResult(
        duration_seconds=1, width=10, height=10,
        objects=[TrackedObjectResult(tracking_id=tid, label=label, first_seen_seconds=0,
                                     last_seen_seconds=1)],
        observations=[ObservationResult(tracking_id=tid, label=label, timestamp_seconds=0,
                                        frame_number=0, bbox=[1, 1, 5, 5])])


def test_merge_prefixes_tracking_ids_so_concepts_cannot_collide():
    merged = merge_results([("mug", sam("mug")), ("hand held pen", sam("pen"))])
    assert [o.tracking_id for o in merged.objects] == ["mug-0", "hand_held_pen-0"]
    assert {o.tracking_id for o in merged.observations} == {"mug-0", "hand_held_pen-0"}


def test_single_concept_keeps_original_tracking_ids():
    assert merge_results([("mug", sam("mug"))]).objects[0].tracking_id == "0"


def test_one_cypher_template_per_relation_type():
    assert set(CREATE_RELATIONSHIP) == set(SPATIAL_RELATION_TYPES)
    assert all(f"[r:{kind} " in cypher for kind, cypher in CREATE_RELATIONSHIP.items())


# --- retrieval refinements found in the live run -----------------------------------------------

def test_near_also_matches_next_to_but_not_the_reverse():
    rels = [stored("r1", "o1", "NEXT_TO", "o3", 0, None)]
    near = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, object_label="pen", relation_type="NEAR"),
                    rels)
    assert [e.graph_id for e in near.evidence] == ["r1"]
    nxt = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, object_label="pen",
                               relation_type="NEXT_TO"), [stored("r2", "o1", "NEAR", "o3", 0, None)])
    assert [e.kind for e in nxt.evidence] == ["note", "relationship"]  # falls back, flagged


def test_unmatched_relation_type_shows_what_was_verified_with_a_note():
    result = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, object_label="mug", relation_type="ON",
                                  time_seconds=5))
    assert result.problem is None
    assert result.evidence[0].kind == "note" and "No ON relationship" in result.evidence[0].text
    assert [e.graph_id for e in result.evidence if e.kind == "relationship"] == ["r1"]


def test_before_appearance_lists_present_objects_even_when_no_relation_matches():
    result = retrieve(QueryIntent(intent=Intent.RELATIONSHIPS, before_appearance_of="book",
                                  relation_type="INSIDE"), rels=[stored("r9", "o1", "ON", "o3", 9000, None)])
    assert result.problem is None
    assert sorted(e.graph_id for e in result.evidence if e.kind == "object") == ["o1", "o3"]
