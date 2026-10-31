"""Deterministic graph retrieval. Each intent maps to fixed repository calls; the model never writes queries."""

from .models import Evidence, Intent, QueryIntent, RetrievalResult


def seconds(ms: int) -> str:
    return f"{ms / 1000:.2f}s"


def _matches(label: str, wanted: str) -> bool:
    label, wanted = label.lower(), wanted.lower()
    return label == wanted or wanted in label or label in wanted


class _Ledger:
    """Allocates stable evidence IDs (O1, E1, B1, ...) for one retrieval."""

    def __init__(self):
        self.items: list[Evidence] = []
        self._counts: dict[str, int] = {}

    def add(self, prefix: str, kind: str, text: str, timestamp_ms=None, graph_id=None, uri=None):
        self._counts[prefix] = self._counts.get(prefix, 0) + 1
        self.items.append(Evidence(evidence_id=f"{prefix}{self._counts[prefix]}", kind=kind,
                                   timestamp_ms=timestamp_ms, text=text, graph_id=graph_id,
                                   evidence_uri=uri))

    def object(self, o: dict):
        self.add("O", "object",
                 f"Tracked object '{o['label']}' (tracking id {o['tracking_id']}) detected "
                 f"between {seconds(o['first_seen_ms'])} and {seconds(o['last_seen_ms'])}.",
                 o["first_seen_ms"], o["object_id"])

    def event(self, e: dict, label: str):
        self.add("E", "event",
                 f"{e['event_type']} of '{label}' from {seconds(e['start_time_ms'])} to "
                 f"{seconds(e['end_time_ms'])}: {e['description']}",
                 e["start_time_ms"], e["event_id"])

    def observation(self, obs: dict, label: str, note: str = ""):
        left, top, right, bottom = obs["bounding_box"]
        self.add("B", "observation",
                 f"'{label}' detected at {seconds(obs['timestamp_ms'])} (frame {obs['frame_index']}), "
                 f"box [{left}, {top}, {right}, {bottom}] px.{note}",
                 obs["timestamp_ms"], obs["observation_id"], obs.get("evidence_uri"))


    def relationship(self, r: dict, labels: dict[str, str]):
        subject = labels.get(r["subject_object_id"], "unknown object")
        target = labels.get(r["target_object_id"], "unknown object")
        start = seconds(r["valid_from_ms"])
        if r.get("valid_to_ms") is None:
            span = (f"from {start}; still holding when last verified at "
                    f"{seconds(r['last_verified_ms'])}")
        else:
            span = f"from {start} until {seconds(r['valid_to_ms'])}"
        confidence = f" (confidence {r['confidence']:.2f})" if r.get("confidence") is not None else ""
        reason = f" Observed: {r['reason']}" if r.get("reason") else ""
        self.add("R", "relationship", f"'{subject}' {r['relation_type']} '{target}' {span}{confidence}."
                 f"{reason}", r["evidence_timestamp_ms"], r["relationship_id"])


class GraphRetriever:
    def __init__(self, repository):
        self.repository = repository

    def retrieve(self, video_id: str, intent: QueryIntent) -> RetrievalResult:
        if intent.intent is Intent.UNSUPPORTED:
            return RetrievalResult(problem="This question is not one MNEMOS memory can answer yet.")
        objects = self.repository.get_video_objects(video_id)
        if not objects:
            return RetrievalResult(problem=f"No objects are stored for video '{video_id}'.")
        selected = objects
        if intent.object_label:
            selected = [o for o in objects if _matches(o["label"], intent.object_label)]
            if not selected:
                known = ", ".join(sorted({o["label"] for o in objects}))
                return RetrievalResult(problem=f"No object matching '{intent.object_label}' in "
                                               f"video '{video_id}'. Known objects: {known}.")
        handler = {
            Intent.LAST_SEEN: self._last_seen,
            Intent.OBJECT_HISTORY: self._object_history,
            Intent.CHANGES: self._changes,
            Intent.SCENE_AT_TIME: self._scene_at_time,
            Intent.RELATIONSHIPS: self._relationships,
        }[intent.intent]
        ledger = _Ledger()
        problem = handler(video_id, intent, selected, ledger)
        return RetrievalResult(evidence=ledger.items, problem=problem)

    def _events_for(self, video_id, selected):
        labels = {o["object_id"]: o["label"] for o in selected}
        return [(e, labels[e["object_id"]]) for e in self.repository.get_video_events(video_id)
                if e["object_id"] in labels]

    def _last_seen(self, video_id, intent, selected, ledger):
        for o in selected:
            ledger.object(o)
            last = self.repository.get_last_observed_position(video_id, o["object_id"])
            if last:
                ledger.observation(last, o["label"], " This is the final detection.")
        for e, label in self._events_for(video_id, selected):
            if e["event_type"] in ("APPEARED", "NO_LONGER_VISIBLE"):
                ledger.event(e, label)

    def _object_history(self, video_id, intent, selected, ledger):
        for o in selected:
            ledger.object(o)
        for e, label in self._events_for(video_id, selected):
            ledger.event(e, label)

    def _changes(self, video_id, intent, selected, ledger):
        start = int((intent.start_seconds or 0) * 1000)
        end = None if intent.end_seconds is None else int(intent.end_seconds * 1000)
        for o in selected:
            ledger.object(o)
        for e, label in self._events_for(video_id, selected):
            if e["end_time_ms"] >= start and (end is None or e["start_time_ms"] <= end):
                ledger.event(e, label)

    def _moment(self, intent, objects):
        """(time_ms, problem). A moment is an explicit time or just before an object first appears."""
        if intent.before_appearance_of:
            anchors = [o for o in objects if _matches(o["label"], intent.before_appearance_of)]
            if not anchors:
                return None, f"No object matching '{intent.before_appearance_of}' was tracked."
            return max(min(o["first_seen_ms"] for o in anchors) - 1, 0), None
        if intent.time_seconds is not None:
            return int(intent.time_seconds * 1000), None
        return None, None

    def _relationships(self, video_id, intent, selected, ledger):
        everything = self.repository.get_video_objects(video_id)
        labels = {o["object_id"]: o["label"] for o in everything}
        t, problem = self._moment(intent, everything)
        if problem:
            return problem
        wanted = {o["object_id"] for o in selected} if intent.object_label else None
        if t is not None and intent.before_appearance_of:
            for o in everything:  # which objects were present is itself part of the answer
                if o["first_seen_ms"] <= t:
                    ledger.object(o)
        stored = self.repository.get_video_relationships(video_id)
        if not stored:
            return "No spatial relationships were verified for this video."
        in_scope = [r for r in stored
                    if (wanted is None or {r["subject_object_id"], r["target_object_id"]} & wanted)
                    and self._in_time(r, intent, t)]
        found = [r for r in in_scope if self._relation_matches(intent.relation_type, r)]
        if not found and intent.relation_type and in_scope:
            # Show what was verified instead, so the answer can say "not X, but Y".
            ledger.add("N", "note", f"No {intent.relation_type} relationship was verified here; "
                                    "the relationships that were verified follow.")
            found = in_scope
        if not found:
            if ledger.items:
                return None
            when = f" at {seconds(t)}" if t is not None else ""
            return f"No matching spatial relationship was verified{when}."
        for r in found:
            ledger.relationship(r, labels)

    @staticmethod
    def _relation_matches(wanted, r):
        # "near" also covers things that are next to it; the reverse is not true.
        return wanted is None or r["relation_type"] == wanted or (
            wanted == "NEAR" and r["relation_type"] == "NEXT_TO")

    def _in_time(self, r, intent, t):
        if t is not None:
            return self._holds_at(r, t)
        if intent.start_seconds is None and intent.end_seconds is None:
            return True
        start = int((intent.start_seconds or 0) * 1000)
        end = None if intent.end_seconds is None else int(intent.end_seconds * 1000)
        return (end is None or r["valid_from_ms"] <= end) and (
            r.get("valid_to_ms") is None or r["valid_to_ms"] > start)

    @staticmethod
    def _holds_at(r, t):
        return r["valid_from_ms"] <= t and (r.get("valid_to_ms") is None or t < r["valid_to_ms"])

    def _scene_at_time(self, video_id, intent, selected, ledger):
        t, problem = self._moment(intent, self.repository.get_video_objects(video_id))
        if problem:
            return problem
        if t is None:
            return "A specific time is needed (e.g. 'at 12 seconds')."
        if intent.before_appearance_of:
            selected = [o for o in selected if o["first_seen_ms"] <= t]
        for o in selected:
            ledger.object(o)
            obs = self.repository.get_observation_at_or_before(video_id, o["object_id"], t)
            if obs:
                lag = t - obs["timestamp_ms"]
                note = " Detected exactly at that time." if lag == 0 else \
                    f" This is the latest detection, {seconds(lag)} before the requested time {seconds(t)}."
                ledger.observation(obs, o["label"], note)
        for e, label in self._events_for(video_id, selected):
            if e["start_time_ms"] <= t <= e["end_time_ms"]:
                ledger.event(e, label)
        labels = {o["object_id"]: o["label"] for o in selected}
        for r in self.repository.get_video_relationships(video_id):
            if (self._holds_at(r, t) and r["subject_object_id"] in labels
                    and r["target_object_id"] in labels):
                ledger.relationship(r, labels)
