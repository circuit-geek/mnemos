import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from backend.api.dependencies import get_ingestion_service, get_query_service
from backend.schemas.videos import (
    ObservationRead,
    ProcessingJobRead,
    VideoAcceptedResponse,
    VideoRead,
)
from backend.services.video_ingestion import VideoIngestionService
from backend.services.video_queries import VideoQueryService

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=VideoAcceptedResponse)
async def upload_video(
    file: UploadFile = File(...),
    service: VideoIngestionService = Depends(get_ingestion_service),
) -> VideoAcceptedResponse:
    video, job = await service.ingest(file.file, file.filename, file.content_type)
    return VideoAcceptedResponse(video_id=video.id, job_id=job.id, status=video.status)


@router.get("/{video_id}", response_model=VideoRead)
async def get_video(
    video_id: uuid.UUID, service: VideoQueryService = Depends(get_query_service)
) -> VideoRead:
    video, job = await service.get_video(video_id)
    result = VideoRead.model_validate(video)
    result.processing_job = ProcessingJobRead.model_validate(job) if job else None
    return result


@router.get("/{video_id}/observations", response_model=list[ObservationRead])
async def list_observations(
    video_id: uuid.UUID,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    service: VideoQueryService = Depends(get_query_service),
) -> list[ObservationRead]:
    return await service.list_observations(video_id, limit, offset)
