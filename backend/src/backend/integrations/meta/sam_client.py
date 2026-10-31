import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Protocol

from backend.core.exceptions import SamProcessingError
from backend.integrations.meta.concept_discovery import ConceptDiscoverer
from backend.integrations.meta.sam_models import VideoProcessingResult
from backend.integrations.meta.sam_parser import parse_sam_artifacts
from backend.reasoning.muse_client import MuseClient

logger = logging.getLogger(__name__)


class SamClient(Protocol):
    async def process_video(
        self, video_path: Path, concepts: list[str] | None = None
    ) -> VideoProcessingResult:
        """`concepts` are the objects to track; None means work out what is in the video."""


class MockSamClient:
    """Replays a saved experiment output directory regardless of the input video."""

    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir

    async def process_video(
        self, video_path: Path, concepts: list[str] | None = None
    ) -> VideoProcessingResult:
        return await asyncio.to_thread(parse_sam_artifacts, self.fixture_dir)


class ScriptSamClient:
    """Runs the existing SAM experiment script, then parses the artifacts it wrote.

    The script prints `Output: <dir>` on success and reads its API key from
    MODEL_API_KEY, which is set here from META_API_KEY.
    """

    def __init__(
        self,
        script_path: Path,
        api_key: str,
        discoverer: ConceptDiscoverer,
        fallback_concept: str = "object",
        concurrency: int = 3,
    ) -> None:
        self.script_path = script_path
        self.api_key = api_key
        self.discoverer = discoverer
        self.fallback_concept = fallback_concept
        self._slots = asyncio.Semaphore(concurrency)

    async def _concepts_for(self, video_path: Path, requested: list[str] | None) -> list[str]:
        """The uploader's concepts win; otherwise ask the model what is in this video."""
        if requested:
            return requested
        try:
            discovered = await self.discoverer.discover(video_path)
        except Exception:
            logger.exception("Concept discovery failed")
            discovered = []
        if not discovered:
            logger.warning("No concepts discovered; falling back to %r", self.fallback_concept)
            return [self.fallback_concept]
        return discovered

    async def process_video(
        self, video_path: Path, concepts: list[str] | None = None
    ) -> VideoProcessingResult:
        """One SAM run per concept (the script tracks a single concept at a time), then merge."""
        concepts = await self._concepts_for(video_path, concepts)
        logger.info("SAM concepts %s", concepts)
        outcomes = await asyncio.gather(
            *(self._run_concept(video_path, c) for c in concepts), return_exceptions=True
        )
        results: list[tuple[str, VideoProcessingResult]] = []
        failures: list[str] = []
        for concept, outcome in zip(concepts, outcomes, strict=True):
            if isinstance(outcome, SamProcessingError):
                logger.warning("SAM found nothing usable for concept=%r: %s", concept, outcome)
                failures.append(f"{concept}: {outcome}")
            elif isinstance(outcome, BaseException):
                raise outcome
            else:
                results.append((concept, outcome))
        if not results:
            raise SamProcessingError("SAM failed for every concept: " + "; ".join(failures))
        return merge_results(results).model_copy(update={"concepts": concepts})

    async def _run_concept(self, video_path: Path, concept: str) -> VideoProcessingResult:
        async with self._slots:
            return await self._run_script(video_path, concept)

    async def _run_script(self, video_path: Path, concept: str) -> VideoProcessingResult:
        env = {**os.environ, "MODEL_API_KEY": self.api_key}
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(self.script_path),
            str(video_path),
            f"--concept={concept}",  # `=` form: a value can never be read as another flag
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise SamProcessingError(f"SAM script failed: {stderr.decode().strip()[-500:]}")
        output_dir = self._output_dir(stdout.decode())
        logger.info("SAM script finished concept=%r output_dir=%s", concept, output_dir)
        return await asyncio.to_thread(parse_sam_artifacts, output_dir)

    @staticmethod
    def _output_dir(stdout: str) -> Path:
        for line in stdout.splitlines():
            if line.startswith("Output: "):
                return Path(line.removeprefix("Output: ").strip())
        raise SamProcessingError("SAM script did not report an output directory")


def merge_results(results: list[tuple[str, VideoProcessingResult]]) -> VideoProcessingResult:
    """Combine per-concept runs. Tracking IDs are only unique within a run, so prefix them."""
    if len(results) == 1:
        return results[0][1]
    objects, observations = [], []
    for concept, result in results:
        prefix = re.sub(r"[^a-z0-9]+", "_", concept.lower()).strip("_") or "concept"
        objects += [o.model_copy(update={"tracking_id": f"{prefix}-{o.tracking_id}"})
                    for o in result.objects]
        observations += [o.model_copy(update={"tracking_id": f"{prefix}-{o.tracking_id}"})
                         for o in result.observations]
    first = results[0][1]
    return VideoProcessingResult(
        duration_seconds=first.duration_seconds, frame_count=first.frame_count,
        width=first.width, height=first.height, objects=objects, observations=observations,
    )


def create_sam_client(settings) -> SamClient:
    if settings.sam_backend == "mock":
        return MockSamClient(settings.sam_fixture_dir)
    if not settings.meta_api_key:
        raise RuntimeError("SAM_BACKEND=script requires META_API_KEY")
    discoverer = ConceptDiscoverer(
        MuseClient(settings.meta_api_key, settings.muse_model),
        frames=settings.sam_discovery_frames,
        max_concepts=settings.sam_max_concepts,
    )
    return ScriptSamClient(
        settings.sam_script_path,
        settings.meta_api_key,
        discoverer=discoverer,
        fallback_concept=settings.sam_concept,
    )
