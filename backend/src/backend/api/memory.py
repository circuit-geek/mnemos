import uuid

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_memory_service, get_query_service
from backend.reasoning.models import Answer
from backend.schemas.memory import (
    AskRequest,
    GraphSnapshot,
    MemoryEvent,
    MemoryObject,
    MemoryObservation,
    MemoryRelationship,
)
from backend.services.memory_queries import MemoryQueryService
from backend.services.video_queries import VideoQueryService

router = APIRouter(prefix="/api/v1/videos/{video_id}", tags=["memory"])


async def _existing_video(
    video_id: uuid.UUID, videos: VideoQueryService = Depends(get_query_service)
) -> uuid.UUID:
    await videos.get_video(video_id)  # 404 for unknown videos
    return video_id


@router.post("/ask", response_model=Answer)
async def ask(
    body: AskRequest,
    video_id: uuid.UUID = Depends(_existing_video),
    memory: MemoryQueryService = Depends(get_memory_service),
) -> Answer:
    return await memory.ask(video_id, body.question)


@router.get("/objects", response_model=list[MemoryObject])
async def list_objects(
    video_id: uuid.UUID = Depends(_existing_video),
    memory: MemoryQueryService = Depends(get_memory_service),
) -> list[MemoryObject]:
    return await memory.objects(video_id)


@router.get("/objects/{object_id}/history", response_model=list[MemoryObservation])
async def object_history(
    object_id: str,
    video_id: uuid.UUID = Depends(_existing_video),
    memory: MemoryQueryService = Depends(get_memory_service),
) -> list[MemoryObservation]:
    return await memory.object_history(video_id, object_id)


@router.get("/events", response_model=list[MemoryEvent])
async def list_events(
    video_id: uuid.UUID = Depends(_existing_video),
    memory: MemoryQueryService = Depends(get_memory_service),
) -> list[MemoryEvent]:
    return await memory.events(video_id)


@router.get("/graph", response_model=GraphSnapshot)
async def graph(
    at_seconds: float | None = Query(None, ge=0),
    video_id: uuid.UUID = Depends(_existing_video),
    memory: MemoryQueryService = Depends(get_memory_service),
) -> GraphSnapshot:
    at_ms = round(at_seconds * 1000) if at_seconds is not None else None
    return await memory.graph(video_id, at_ms)


@router.get("/relationships", response_model=list[MemoryRelationship])
async def list_relationships(
    at_seconds: float | None = Query(None, ge=0),
    object_id: str | None = None,
    video_id: uuid.UUID = Depends(_existing_video),
    memory: MemoryQueryService = Depends(get_memory_service),
) -> list[MemoryRelationship]:
    at_ms = round(at_seconds * 1000) if at_seconds is not None else None
    return await memory.relationships(video_id, at_ms, object_id)
