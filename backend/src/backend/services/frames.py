"""Serve a single JPEG frame of a stored video; the only input is a video ID and a timestamp."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import FrameNotFoundError, VideoNotFoundError
from backend.integrations.media.frames import extract_frame_jpeg
from backend.integrations.storage.base import ObjectStorage
from backend.repositories.videos import VideoRepository


def frame_url(video_id: uuid.UUID | str, timestamp_ms: int) -> str:
    """Relative API path of the frame at `timestamp_ms`; what the frontend gets as evidence."""
    return f"/api/v1/videos/{video_id}/frames/{timestamp_ms}"


class FrameService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage) -> None:
        self.videos = VideoRepository(session)
        self.storage = storage

    async def frame_jpeg(self, video_id: uuid.UUID, timestamp_ms: int) -> bytes:
        video = await self.videos.get(video_id)
        if video is None:
            raise VideoNotFoundError(f"Video {video_id} not found")
        limit_ms = video.duration_seconds * 1000 + 500 if video.duration_seconds else None
        if limit_ms is not None and timestamp_ms > limit_ms:
            raise FrameNotFoundError(f"Timestamp {timestamp_ms}ms is past the end of the video")
        async with self.storage.open_local_copy(video.storage_key) as path:
            return await extract_frame_jpeg(str(path), timestamp_ms)
