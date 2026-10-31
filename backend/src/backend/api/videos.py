import uuid

from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse

from backend.api.dependencies import (
    get_container,
    get_frame_service,
    get_ingestion_service,
    get_query_service,
)
from backend.container import AppContainer
from backend.core.concepts import parse_concepts
from backend.schemas.videos import (
    ObservationRead,
    ProcessingJobRead,
    VideoAcceptedResponse,
    VideoRead,
)
from backend.services.frames import FrameService
from backend.services.video_ingestion import VideoIngestionService
from backend.services.video_queries import VideoQueryService

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=VideoAcceptedResponse)
async def upload_video(
    file: UploadFile = File(...),
    concepts: str | None = Form(
        None,
        description="Comma-separated objects to track (e.g. 'mug, notebook'). "
        "Omit to let the model discover them from the video.",
    ),
    service: VideoIngestionService = Depends(get_ingestion_service),
) -> VideoAcceptedResponse:
    video, job = await service.ingest(
        file.file, file.filename, file.content_type, parse_concepts(concepts)
    )
    return VideoAcceptedResponse(video_id=video.id, job_id=job.id, status=video.status)


def _read(video, job, object_count: int | None = None) -> VideoRead:
    result = VideoRead.model_validate(video)
    result.processing_job = ProcessingJobRead.model_validate(job) if job else None
    result.object_count = object_count
    return result


@router.get("", response_model=list[VideoRead])
async def list_videos(
    limit: int = Query(50, ge=1, le=200),
    service: VideoQueryService = Depends(get_query_service),
) -> list[VideoRead]:
    return [_read(v, job, n) for v, job, n in await service.list_videos(limit)]


@router.get("/{video_id}/media", response_class=FileResponse)
async def get_media(
    video_id: uuid.UUID,
    service: VideoQueryService = Depends(get_query_service),
    container: AppContainer = Depends(get_container),
):
    """The original upload, for playback. Supports HTTP range requests so seeking works."""
    video, _ = await service.get_video(video_id)
    reference = await container.storage.get_download_reference(video.storage_key)
    if reference.startswith(("http://", "https://")):
        return RedirectResponse(reference)
    return FileResponse(reference, media_type=video.content_type)


@router.get("/{video_id}", response_model=VideoRead)
async def get_video(
    video_id: uuid.UUID, service: VideoQueryService = Depends(get_query_service)
) -> VideoRead:
    video, job = await service.get_video(video_id)
    return _read(video, job)


@router.get("/{video_id}/observations", response_model=list[ObservationRead])
async def list_observations(
    video_id: uuid.UUID,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    service: VideoQueryService = Depends(get_query_service),
) -> list[ObservationRead]:
    return await service.list_observations(video_id, limit, offset)


@router.get("/{video_id}/frames/{timestamp_ms}", response_class=Response)
async def get_frame(
    video_id: uuid.UUID,
    timestamp_ms: int = Path(ge=0),
    service: FrameService = Depends(get_frame_service),
) -> Response:
    jpeg = await service.frame_jpeg(video_id, timestamp_ms)
    return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})
