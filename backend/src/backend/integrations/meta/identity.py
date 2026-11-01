"""Conservative re-linking of tracks that SAM split when an object left view and came back.

SAM gives a returning object a new tracking ID, so one mug can become two "objects". Linking is
only done when it is unambiguous, and always reported (`linked_tracks`) so it is never silent.
"""

from collections import defaultdict

from backend.integrations.meta.sam_models import (
    ObservationResult,
    TrackedObjectResult,
    VideoProcessingResult,
)

DEFAULT_MAX_GAP_SECONDS = 8.0


def link_split_tracks(
    result: VideoProcessingResult, max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS
) -> VideoProcessingResult:
    """Merge same-label tracks that never overlap, are separated by a short gap, and where no
    other track of that label is visible during the gap (so it cannot be a different instance)."""
    by_label: dict[str | None, list[TrackedObjectResult]] = defaultdict(list)
    for track in result.objects:
        by_label[track.label].append(track)

    head_of: dict[str, str] = {}  # tracking_id -> id of the track it was merged into
    merged: list[TrackedObjectResult] = []
    linked: dict[str, list[str]] = {}
    for label, tracks in by_label.items():
        tracks = sorted(tracks, key=lambda t: (t.first_seen_seconds, t.tracking_id))
        groups: list[list[TrackedObjectResult]] = []
        for track in tracks:
            if groups and label is not None and _can_link(groups[-1], track, tracks, max_gap_seconds):
                groups[-1].append(track)
            else:
                groups.append([track])
        for group in groups:
            head = group[0]
            for member in group[1:]:
                head_of[member.tracking_id] = head.tracking_id
            if len(group) > 1:
                linked[head.tracking_id] = [m.tracking_id for m in group[1:]]
            merged.append(head.model_copy(update={
                "last_seen_seconds": max(m.last_seen_seconds for m in group)}))
    if not linked:
        return result
    observations = [
        o.model_copy(update={"tracking_id": head_of[o.tracking_id]}) if o.tracking_id in head_of else o
        for o in result.observations
    ]
    return result.model_copy(update={
        "objects": merged, "observations": _sorted(observations), "linked_tracks": linked})


def _can_link(group, nxt, label_tracks, max_gap_seconds) -> bool:
    last = max(m.last_seen_seconds for m in group)
    gap = nxt.first_seen_seconds - last
    if not 0 < gap <= max_gap_seconds:
        return False
    members = {id(m) for m in group} | {id(nxt)}
    for other in label_tracks:
        if id(other) in members:
            continue
        # Another instance of the same kind is visible during the gap: ambiguous, do not link.
        if other.first_seen_seconds < nxt.first_seen_seconds and other.last_seen_seconds > last:
            return False
    return True


def _sorted(observations: list[ObservationResult]) -> list[ObservationResult]:
    return sorted(observations, key=lambda o: (o.timestamp_seconds, o.frame_number, o.tracking_id))
