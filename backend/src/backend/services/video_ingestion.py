import logging
import os
import uuid
from pathlib import PurePath
from typing import BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import (
    InvalidVideoError,
    UnsupportedMediaTypeError,
    VideoTooLargeError,
)
from backend.integrations.storage.base import ObjectStorage
from backend.models import JobStatus, JobType, ProcessingJob, Video, VideoStatus
from backend.repositories.processing_jobs import ProcessingJobRepository
from backend.repositories.videos import VideoRepository
from backend.workers.dispatcher import ProcessingDispatcher

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


def _looks_like_video(content_type: str, header: bytes) -> bool:
    """Check container magic bytes so a spoofed Content-Type is rejected."""
    if content_type == "video/webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")  # EBML
    return header[4:8] == b"ftyp"  # ISO base media (mp4 / mov)


class VideoIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage,
        dispatcher: ProcessingDispatcher,
        max_upload_bytes: int,
    ) -> None:
        self.session = session
        self.storage = storage
        self.dispatcher = dispatcher
        self.max_upload_bytes = max_upload_bytes
        self.videos = VideoRepository(session)
        self.jobs = ProcessingJobRepository(session)

    async def ingest(
        self,
        data: BinaryIO,
        original_filename: str | None,
        content_type: str | None,
        concepts: list[str] | None = None,
    ) -> tuple[Video, ProcessingJob]:
        content_type = (content_type or "").split(";")[0].strip().lower()
        size = self._validate(data, content_type)

        video_id = uuid.uuid4()
        safe_name = (
            PurePath(original_filename or "").name or f"upload{ALLOWED_CONTENT_TYPES[content_type]}"
        )
        stored_name = f"original{ALLOWED_CONTENT_TYPES[content_type]}"
        storage_key = f"videos/{video_id}/{stored_name}"
        logger.info("Video accepted video_id=%s size_bytes=%d", video_id, size)

        data.seek(0)
        size = await self.storage.upload_file(storage_key, data, content_type)
        logger.info("Video upload stored video_id=%s key=%s", video_id, storage_key)

        try:
            video = await self.videos.add(
                Video(
                    id=video_id,
                    filename=stored_name,
                    original_filename=safe_name[:255],
                    content_type=content_type,
                    storage_key=storage_key,
                    size_bytes=size,
                    requested_concepts=concepts,
                    status=VideoStatus.UPLOADED,
                )
            )
            job = await self.jobs.add(
                ProcessingJob(
                    video_id=video_id,
                    status=JobStatus.PENDING,
                    job_type=JobType.VIDEO_PROCESSING,
                )
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.storage.delete_file(storage_key)
            raise

        # QUEUED must be committed before dispatch so a fast worker never sees it overwritten.
        await self.videos.set_status(video, VideoStatus.QUEUED)
        await self.session.commit()
        try:
            await self.dispatcher.dispatch_video_processing(video.id, job.id)
        except Exception as exc:
            logger.exception("Dispatch failed video_id=%s", video.id)
            await self.videos.set_status(video, VideoStatus.FAILED)
            await self.jobs.mark_failed(job, f"Dispatch failed: {exc}"[:1000])
            await self.session.commit()
            raise
        logger.info("Processing job queued video_id=%s job_id=%s", video.id, job.id)
        return video, job

    def _validate(self, data: BinaryIO, content_type: str) -> int:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UnsupportedMediaTypeError(
                f"Unsupported content type {content_type!r}; allowed: "
                + ", ".join(sorted(ALLOWED_CONTENT_TYPES))
            )
        size = data.seek(0, os.SEEK_END)
        data.seek(0)
        if size == 0:
            raise InvalidVideoError("Uploaded file is empty")
        if size > self.max_upload_bytes:
            raise VideoTooLargeError(f"Upload exceeds the {self.max_upload_bytes}-byte limit")
        if not _looks_like_video(content_type, data.read(12)):
            raise InvalidVideoError("File content does not match the declared video type")
        return size
