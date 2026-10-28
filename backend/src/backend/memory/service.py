"""Ingest saved tracking artifacts into temporal graph memory."""

from pathlib import Path

from .events import EventDetector
from .models import IngestionSummary
from .transformer import ObservationTransformer


class MemoryIngestionService:
    def __init__(self, repository, transformer: ObservationTransformer | None = None,
                 event_detector: EventDetector | None = None):
        self.repository = repository
        self.transformer = transformer or ObservationTransformer()
        self.event_detector = event_detector or EventDetector()

    def ingest(self, metadata_path: Path, observations_path: Path, video_id: str,
               tracking_summary_path: Path | None = None) -> IngestionSummary:
        batch = self.transformer.load(metadata_path, observations_path, video_id,
                                      tracking_summary_path)
        events = self.event_detector.detect(batch)
        self.repository.initialize_schema()
        created = self.repository.ingest(batch, events)
        return IngestionSummary(video_id=video_id, objects_created=created,
                                observations_processed=len(batch.observations),
                                events_detected=len(events))
