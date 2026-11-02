"""Single-frame extraction with ffmpeg; callers pass a trusted local path and a timestamp."""

import asyncio
import logging

from backend.core.exceptions import FrameNotFoundError

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT_SECONDS = 30


async def extract_frame_jpeg(path: str, timestamp_ms: int, max_width: int | None = None) -> bytes:
    """One JPEG frame at `timestamp_ms`. Seeking onto or past the last frame's start time yields
    nothing in ffmpeg, so fall back to slightly earlier times (still the closest frame)."""
    for back_off_ms in (0, 150, 400):
        frame = await _extract_once(path, max(timestamp_ms - back_off_ms, 0), max_width)
        if frame:
            return frame
    raise FrameNotFoundError(f"No frame at {timestamp_ms}ms")


async def _extract_once(path: str, timestamp_ms: int, max_width: int | None) -> bytes:
    command = ["ffmpeg", "-v", "error", "-ss", f"{timestamp_ms / 1000:.3f}", "-i", path,
               "-frames:v", "1"]
    # MJPEG needs full-range YUV; newer ffmpeg refuses the limited-range output of most H.264.
    filters = [f"scale='min({max_width},iw)':-2"] if max_width else []
    filters.append("format=yuvj420p")
    command += ["-vf", ",".join(filters), "-f", "image2pipe", "-vcodec", "mjpeg", "-"]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        out, err = await asyncio.wait_for(process.communicate(), FFMPEG_TIMEOUT_SECONDS)
    except TimeoutError:
        process.kill()
        raise FrameNotFoundError("Frame extraction timed out") from None
    if process.returncode != 0:
        logger.warning("ffmpeg failed: %s", err.decode(errors="replace")[:300])
        raise FrameNotFoundError("Frame extraction failed")
    return out


async def probe_duration_ms(path: str) -> int:
    process = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await asyncio.wait_for(process.communicate(), FFMPEG_TIMEOUT_SECONDS)
    try:
        return round(float(out.decode().strip()) * 1000)
    except ValueError:
        raise FrameNotFoundError("Could not read the video duration") from None
