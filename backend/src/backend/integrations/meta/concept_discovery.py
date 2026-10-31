"""Find what is worth tracking in a video: Muse Spark looks at a few frames and names the objects.

SAM tracks one noun phrase per run, so the discovered names become SAM's concepts.
"""

import asyncio
import logging
from pathlib import Path

from backend.integrations.media.frames import extract_frame_jpeg, probe_duration_ms

logger = logging.getLogger(__name__)

DISCOVERY_INSTRUCTIONS = """You are given several frames sampled across one video, in time order.
List the distinct physical objects that appear in it which are worth tracking.
Return ONLY JSON: {"objects": [{"name": string}]}.
Rules:
- Include objects that appear in any frame, even briefly or only at the start or end.
- Each name is a short, common, singular noun phrase an image segmenter understands
  ("mug", "laptop", "notebook", "phone", "pen", "bag"), at most three words, lowercase.
- Only separate, movable, concrete things. Exclude people and body parts (hands, arms), surfaces and
  background (table, desk, floor, wall, cloth), and anything you are not sure is an object.
- One entry per kind of object: do not list the same kind twice, even if several are visible.
- Most prominent first. Return an empty list if nothing qualifies."""

# Backstop for the rules above: surfaces and body parts are not tracked objects.
EXCLUDED = {"table", "desk", "floor", "wall", "ceiling", "background", "surface", "tablecloth",
            "cloth", "hand", "hands", "arm", "finger", "fingers", "person", "people", "man",
            "woman", "table cover", "countertop", "room"}


class ConceptDiscoverer:
    def __init__(self, muse, frames: int = 6, max_concepts: int = 5, max_frame_width: int = 640):
        self.muse = muse
        self.frames = frames
        self.max_concepts = max_concepts
        self.max_frame_width = max_frame_width

    async def discover(self, video_path: Path) -> list[str]:
        duration_ms = await probe_duration_ms(str(video_path))
        times = [round(duration_ms * (i + 0.5) / self.frames) for i in range(self.frames)]
        images = [await extract_frame_jpeg(str(video_path), t, self.max_frame_width) for t in times]
        raw = await asyncio.to_thread(
            self.muse.generate_json, DISCOVERY_INSTRUCTIONS,
            {"frame_times_seconds": [round(t / 1000, 1) for t in times]}, images=images)
        concepts = self.clean(raw)[: self.max_concepts]
        logger.info("Discovered concepts %s", concepts)
        return concepts

    @staticmethod
    def clean(raw: dict) -> list[str]:
        entries = raw.get("objects")
        names: list[str] = []
        for entry in entries if isinstance(entries, list) else []:
            name = entry.get("name") if isinstance(entry, dict) else None
            if not isinstance(name, str):
                continue
            name = " ".join(name.lower().split())
            if (not name or len(name) > 40 or len(name.split()) > 3 or name in EXCLUDED
                    or name in names):
                continue
            names.append(name)
        return names
