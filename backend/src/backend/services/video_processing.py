import asyncio
import logging
import uuid
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.meta.sam_client import SamClient
from backend.integrations.meta.sam_models import VideoProcessingResult
from backend.integrations.neo4j.graph_writer import GraphWriter, build_memory_batch
from backend.integrations.storage.base import ObjectStorage
from backend.models import Observation, TrackedObject, Video, VideoStatus
from backend.repositories.observations import ObservationRepository
from backend.repositories.processing_jobs import ProcessingJobRepository
from backend.repositories.tracked_objects import TrackedObjectRepository
from backend.repositories.videos import VideoRepository
from backend.scene.scene_service import SceneAnalyzer

logger = logging.getLogger(__name__)


class Stage(StrEnum):
    """Pipeline stages in order; each is set only when the work actually begins."""

    QUEUED = "queued"
    DISCOVERING = "discovering"
    TRACKING = "tracking"
    BUILDING_MEMORY = "building_memory"
    ANALYZING_SCENE = "analyzing_scene"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoProcessingService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage,
        sam: SamClient,
        graph: GraphWriter,
        scene: SceneAnalyzer | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.sam = sam
        self.graph = graph
        self.scene = scene
        self.videos = VideoRepository(session)
        self.jobs = ProcessingJobRepository(session)
        self.tracked_objects = TrackedObjectRepository(session)
        self.observations = ObservationRepository(session)
        self._commit_lock = asyncio.Lock()

    async def process(self, video_id: uuid.UUID, job_id: uuid.UUID) -> None:
        ids = f"video_id={video_id} job_id={job_id}"
        video = await self.videos.get(video_id)
        job = await self.jobs.get(job_id)
        if video is None or job is None:
            logger.error("Processing requested for unknown video/job %s", ids)
            return
        try:
            await self.videos.set_status(video, VideoStatus.PROCESSING)
            await self.jobs.mark_running(job)
            await self._stage(job, Stage.TRACKING)
            logger.info("Processing started %s", ids)

            async with self.storage.open_local_copy(video.storage_key) as video_path:
                result = await self.sam.process_video(
                    video_path, video.requested_concepts, lambda s, d: self._stage(job, s, d)
                )
            logger.info(
                "SAM processing finished %s objects=%d observations=%d",
                ids,
                len(result.objects),
                len(result.observations),
            )

            await self._stage(job, Stage.BUILDING_MEMORY, "Saving observations and events")
            await self._persist(video, result)
            logger.info("Observations persisted %s", ids)

            await self.graph.write_video_graph(
                video.id, video.original_filename, video.created_at, result
            )
            logger.info("Graph update finished %s", ids)

            await self._analyze_scene(video, job, result, ids)

            await self.videos.set_status(video, VideoStatus.COMPLETED)
            job.stage, job.stage_detail = Stage.COMPLETED, None
            await self.jobs.mark_completed(job)
            await self.session.commit()
            logger.info("Processing completed %s", ids)
        except Exception as exc:
            logger.exception("Processing failed %s", ids)
            await self._mark_failed(video_id, job_id, exc)

    async def _stage(self, job, stage: str, detail: str | None = None) -> None:
        """Record and commit the stage reached. Callbacks may overlap, so serialise the session."""
        async with self._commit_lock:
            job.stage, job.stage_detail = str(stage), detail[:255] if detail else None
            await self.session.commit()

    async def _analyze_scene(
        self, video: Video, job, result: VideoProcessingResult, ids: str
    ) -> None:
        """Spatial relations enrich the temporal memory; if they fail the video still completes
        with its temporal memory, and the failure is logged."""
        if self.scene is None:
            return
        try:
            await self._stage(job, Stage.ANALYZING_SCENE, "Verifying spatial relationships")
            batch = build_memory_batch(video.id, video.original_filename, video.created_at, result)
            async with self.storage.open_local_copy(video.storage_key) as video_path:
                relationships = await self.scene.analyze(
                    video_path, batch, (result.width, result.height)
                )
            await self.graph.write_relationships(video.id, relationships)
            logger.info("Spatial relationships stored %s count=%d", ids, len(relationships))
        except Exception:
            logger.exception("Scene analysis failed; continuing without spatial memory %s", ids)

    async def _persist(self, video: Video, result: VideoProcessingResult) -> None:
        # Re-processing replaces earlier output instead of duplicating it.
        await self.observations.delete_for_video(video.id)
        await self.tracked_objects.delete_for_video(video.id)
        tracked = {
            o.tracking_id: TrackedObject(
                video_id=video.id,
                external_tracking_id=o.tracking_id,
                label=o.label,
                first_seen_at=o.first_seen_seconds,
                last_seen_at=o.last_seen_seconds,
                attributes={},
            )
            for o in result.objects
        }
        await self.tracked_objects.add_many(list(tracked.values()))
        await self.observations.add_many(
            [
                Observation(
                    video_id=video.id,
                    tracked_object_id=tracked[o.tracking_id].id,
                    timestamp_seconds=o.timestamp_seconds,
                    frame_number=o.frame_number,
                    label=o.label,
                    confidence=o.confidence,
                    bbox=o.bbox,
                    attributes={"evidence_uri": o.evidence_uri} if o.evidence_uri else {},
                )
                for o in result.observations
            ]
        )
        video.tracked_concepts = result.concepts or None
        video.width, video.height = result.width, result.height
        if result.duration_seconds is not None:
            video.duration_seconds = result.duration_seconds

    async def _mark_failed(self, video_id: uuid.UUID, job_id: uuid.UUID, exc: Exception) -> None:
        await self.session.rollback()
        video = await self.videos.get(video_id)
        job = await self.jobs.get(job_id)
        if video is not None:
            await self.videos.set_status(video, VideoStatus.FAILED)
        if job is not None:
            job.stage, job.stage_detail = Stage.FAILED, None
            await self.jobs.mark_failed(job, f"{type(exc).__name__}: {exc}"[:1000])
        await self.session.commit()
