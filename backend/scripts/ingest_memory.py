#!/usr/bin/env python3
"""Ingest one saved SAM experiment into Neo4j (environment variables only)."""

import argparse
import json
import os
from pathlib import Path

from backend.memory.events import EventDetector
from backend.memory.repository import Neo4jMemoryRepository
from backend.memory.service import MemoryIngestionService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--movement-threshold-px", type=float, default=50)
    parser.add_argument("--missing-threshold-ms", type=int, default=1000)
    args = parser.parse_args()
    required = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        parser.error("Missing environment variables: " + ", ".join(missing))
    directory = args.artifact_dir
    with Neo4jMemoryRepository.connect(os.environ["NEO4J_URI"],
                                       os.environ["NEO4J_USERNAME"],
                                       os.environ["NEO4J_PASSWORD"],
                                       os.environ.get("NEO4J_DATABASE")) as repository:
        service = MemoryIngestionService(repository, event_detector=EventDetector(
            movement_threshold_px=args.movement_threshold_px,
            missing_threshold_ms=args.missing_threshold_ms,
        ))
        summary_path = directory / "tracking_summary.json"
        summary = service.ingest(directory / "metadata.json", directory / "observations.json",
                                 args.video_id, summary_path if summary_path.is_file() else None)
    print(json.dumps(summary.model_dump(), indent=2))


if __name__ == "__main__":
    main()
