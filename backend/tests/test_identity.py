from backend.integrations.meta.identity import link_split_tracks
from backend.integrations.meta.sam_models import (
    ObservationResult,
    TrackedObjectResult,
    VideoProcessingResult,
)


def track(tid, label, first, last):
    return TrackedObjectResult(tracking_id=tid, label=label, first_seen_seconds=first,
                               last_seen_seconds=last)


def result(*tracks):
    observations = []
    for t in tracks:
        for i, ts in enumerate((t.first_seen_seconds, t.last_seen_seconds)):
            observations.append(ObservationResult(
                tracking_id=t.tracking_id, label=t.label, timestamp_seconds=ts,
                frame_number=int(ts * 10) + i, bbox=[1, 1, 5, 5]))
    return VideoProcessingResult(duration_seconds=30, objects=list(tracks), observations=observations)


def test_object_that_left_and_returned_becomes_one_track_with_a_gap():
    linked = link_split_tracks(result(track("mug-0", "mug", 0, 9.7), track("mug-1", "mug", 15.2, 21)))
    [mug] = linked.objects
    assert (mug.tracking_id, mug.first_seen_seconds, mug.last_seen_seconds) == ("mug-0", 0, 21)
    assert {o.tracking_id for o in linked.observations} == {"mug-0"}
    assert linked.linked_tracks == {"mug-0": ["mug-1"]}
    times = [o.timestamp_seconds for o in linked.observations]
    assert times == sorted(times)


def test_a_chain_of_returns_links_into_one_track():
    linked = link_split_tracks(result(track("a", "pen", 0, 3), track("b", "pen", 5, 8), track("c", "pen", 10, 12)))
    assert [t.tracking_id for t in linked.objects] == ["a"]
    assert linked.linked_tracks == {"a": ["b", "c"]}


def test_different_labels_are_never_linked():
    linked = link_split_tracks(result(track("m", "mug", 0, 5), track("p", "pen", 7, 9)))
    assert len(linked.objects) == 2 and linked.linked_tracks == {}


def test_overlapping_tracks_are_different_objects():
    assert len(link_split_tracks(result(track("a", "mug", 0, 10), track("b", "mug", 8, 14))).objects) == 2


def test_long_gap_is_not_linked():
    assert len(link_split_tracks(result(track("a", "mug", 0, 2), track("b", "mug", 20, 25))).objects) == 2


def test_ambiguous_when_another_instance_is_visible_during_the_gap():
    # a second mug stays in view the whole time, so the returning one could be anyone
    tracks = (track("a", "mug", 0, 5), track("c", "mug", 0, 30), track("b", "mug", 9, 12))
    linked = link_split_tracks(result(*tracks))
    assert len(linked.objects) == 3 and linked.linked_tracks == {}


def test_result_is_unchanged_when_nothing_links():
    original = result(track("a", "mug", 0, 5))
    assert link_split_tracks(original) is original
