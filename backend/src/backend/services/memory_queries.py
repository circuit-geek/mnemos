"""Read-side access to temporal memory; the Neo4j driver is synchronous, so calls run in threads."""

import asyncio
import uuid

from backend.core.exceptions import MemoryUnavailableError
from backend.reasoning.models import Answer
from backend.reasoning.reasoning_service import ReasoningService
from backend.schemas.memory import (
    FullObservation,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    MemoryBundle,
    MemoryEvent,
    MemoryObject,
    MemoryObservation,
    MemoryRelationship,
)
from backend.services.frames import frame_url


class MemoryQueryService:
    def __init__(self, repository, reasoning: ReasoningService | None) -> None:
        if repository is None:
            raise MemoryUnavailableError("Temporal memory is not enabled (set NEO4J_ENABLED=true)")
        self.repository = repository
        self.reasoning = reasoning

    @staticmethod
    def _observation(video_id: uuid.UUID, row: dict) -> MemoryObservation:
        obs = MemoryObservation.model_validate(row)
        return obs.model_copy(update={"evidence_uri": frame_url(video_id, obs.timestamp_ms)})

    async def ask(self, video_id: uuid.UUID, question: str) -> Answer:
        if self.reasoning is None:
            raise MemoryUnavailableError("Reasoning is not configured (set META_API_KEY)")
        answer = await asyncio.to_thread(self.reasoning.ask, str(video_id), question)
        # Stored evidence_uri values are server-local; expose a frame URL instead.
        evidence = [
            e.model_copy(update={"evidence_uri": (
                frame_url(video_id, e.timestamp_ms) if e.timestamp_ms is not None else None)})
            for e in answer.evidence
        ]
        return answer.model_copy(update={"evidence": evidence})

    async def objects(self, video_id: uuid.UUID) -> list[MemoryObject]:
        rows = await asyncio.to_thread(self.repository.get_video_objects, str(video_id))
        return [MemoryObject.model_validate(r, from_attributes=False) for r in rows]

    async def events(self, video_id: uuid.UUID) -> list[MemoryEvent]:
        rows = await asyncio.to_thread(self.repository.get_video_events, str(video_id))
        return [MemoryEvent.model_validate(r) for r in rows]

    async def relationships(
        self, video_id: uuid.UUID, at_ms: int | None = None, object_id: str | None = None
    ) -> list[MemoryRelationship]:
        """Spatial relations; with `at_ms`, only those holding at that moment."""
        rows = await asyncio.to_thread(self.repository.get_video_relationships, str(video_id))
        found = []
        for row in rows:
            if at_ms is not None and not (
                row["valid_from_ms"] <= at_ms
                and (row.get("valid_to_ms") is None or at_ms < row["valid_to_ms"])
            ):
                continue
            if object_id and object_id not in (row["subject_object_id"], row["target_object_id"]):
                continue
            found.append(MemoryRelationship.model_validate(
                {**row, "evidence_uri": frame_url(video_id, row["evidence_timestamp_ms"])}
            ))
        return found

    async def bundle(self, video_id: uuid.UUID) -> MemoryBundle:
        """Full history in one response. Relationship start/end events are derived from the
        stored relationship intervals, not stored or invented."""
        rows = await asyncio.to_thread(self.repository.get_video_observations, str(video_id))
        objects = await self.objects(video_id)
        relationships = await self.relationships(video_id)
        events = await self.events(video_id)
        labels = {o.object_id: o.label for o in objects}
        for r in relationships:
            subject = labels.get(r.subject_object_id, "?")
            target = labels.get(r.target_object_id, "?")
            for suffix, at, kind, verb in (
                ("start", r.valid_from_ms, "RELATIONSHIP_STARTED", "began"),
                ("end", r.valid_to_ms, "RELATIONSHIP_ENDED", "ended"),
            ):
                if at is None:
                    continue
                events.append(MemoryEvent(
                    event_id=f"{r.relationship_id}:{suffix}", object_id=r.subject_object_id,
                    related_object_id=r.target_object_id, relationship_id=r.relationship_id,
                    event_type=kind, start_time_ms=at, end_time_ms=at, confidence=r.confidence,
                    description=f"{subject} {r.relation_type} {target} {verb}",
                ))
        events.sort(key=lambda e: (e.start_time_ms, e.event_id))
        observations = [FullObservation.model_validate(
            {**row, "evidence_uri": frame_url(video_id, row["timestamp_ms"])}) for row in rows]
        return MemoryBundle(video_id=str(video_id), objects=objects, observations=observations,
                            events=events, relationships=relationships)

    async def object_history(self, video_id: uuid.UUID, object_id: str) -> list[MemoryObservation]:
        rows = await asyncio.to_thread(self.repository.get_object_history, str(video_id), object_id)
        return [self._observation(video_id, r) for r in rows]

    async def graph(self, video_id: uuid.UUID, at_ms: int | None) -> GraphSnapshot:
        """Graph as known at `at_ms` (everything up to that moment); whole recording when None."""
        vid = str(video_id)
        objects = await self.objects(video_id)
        events = await self.events(video_id)
        nodes = [GraphNode(id=vid, type="video", label="video")]
        edges: list[GraphEdge] = []
        shown: set[str] = set()
        for obj in objects:
            if at_ms is not None and obj.first_seen_ms > at_ms:
                continue
            shown.add(obj.object_id)
            data = obj.model_dump()
            if at_ms is not None:
                last = await asyncio.to_thread(
                    self.repository.get_observation_at_or_before, vid, obj.object_id, at_ms
                )
                data["last_observation"] = (
                    self._observation(video_id, last).model_dump() if last else None
                )
            nodes.append(GraphNode(id=obj.object_id, type="object", label=obj.label, data=data))
            edges.append(
                GraphEdge(id=f"{vid}>{obj.object_id}", source=vid, target=obj.object_id,
                          type="HAS_OBJECT")
            )
        for rel in await self.relationships(video_id, at_ms):
            if rel.subject_object_id in shown and rel.target_object_id in shown:
                edges.append(GraphEdge(
                    id=rel.relationship_id, source=rel.subject_object_id,
                    target=rel.target_object_id, type=rel.relation_type, data=rel.model_dump(),
                ))
        for event in events:
            if event.object_id not in shown or (at_ms is not None and event.start_time_ms > at_ms):
                continue
            nodes.append(GraphNode(id=event.event_id, type="event", label=event.event_type,
                                   data=event.model_dump()))
            edges.append(
                GraphEdge(id=f"{event.object_id}>{event.event_id}", source=event.object_id,
                          target=event.event_id, type="PARTICIPATED_IN")
            )
        return GraphSnapshot(video_id=vid, at_ms=at_ms, nodes=nodes, edges=edges)
