import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Protocol

from backend.core.exceptions import SamProcessingError
from backend.integrations.meta.sam_models import VideoProcessingResult
from backend.integrations.meta.sam_parser import parse_sam_artifacts

logger = logging.getLogger(__name__)


class SamClient(Protocol):
    async def process_video(self, video_path: Path) -> VideoProcessingResult: ...


class MockSamClient:
    """Replays a saved experiment output directory regardless of the input video."""

    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir

    async def process_video(self, video_path: Path) -> VideoProcessingResult:
        return await asyncio.to_thread(parse_sam_artifacts, self.fixture_dir)


class ScriptSamClient:
    """Runs the existing SAM experiment script, then parses the artifacts it wrote.

    The script prints `Output: <dir>` on success and reads its API key from
    MODEL_API_KEY, which is set here from META_API_KEY.
    """

    def __init__(self, script_path: Path, concept: str, api_key: str) -> None:
        self.script_path = script_path
        self.concept = concept
        self.api_key = api_key

    async def process_video(self, video_path: Path) -> VideoProcessingResult:
        env = {**os.environ, "MODEL_API_KEY": self.api_key}
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(self.script_path),
            str(video_path),
            "--concept",
            self.concept,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise SamProcessingError(f"SAM script failed: {stderr.decode().strip()[-500:]}")
        output_dir = self._output_dir(stdout.decode())
        logger.info("SAM script finished output_dir=%s", output_dir)
        return await asyncio.to_thread(parse_sam_artifacts, output_dir)

    @staticmethod
    def _output_dir(stdout: str) -> Path:
        for line in stdout.splitlines():
            if line.startswith("Output: "):
                return Path(line.removeprefix("Output: ").strip())
        raise SamProcessingError("SAM script did not report an output directory")


def create_sam_client(settings) -> SamClient:
    if settings.sam_backend == "mock":
        return MockSamClient(settings.sam_fixture_dir)
    if not settings.meta_api_key:
        raise RuntimeError("SAM_BACKEND=script requires META_API_KEY")
    return ScriptSamClient(settings.sam_script_path, settings.sam_concept, settings.meta_api_key)
