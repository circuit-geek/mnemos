"""Turn saved SAM experiment artifacts into the internal result models.

Validation (frame bounds, bbox convention, summary consistency) is delegated to the
existing `ObservationTransformer`; this module only reshapes its output.
"""

from pathlib import Path

from backend.core.exceptions import SamProcessingError
from backend.integrations.meta.sam_models import (
    ObservationResult,
    TrackedObjectResult,
    VideoProcessingResult,
)
from backend.memory.transformer import ObservationTransformer, read_json

# Placeholder only: ids derived by the transformer are not used here.
_PLACEHOLDER_VIDEO_ID = "unassigned"


def parse_sam_artifacts(artifact_dir: Path) -> VideoProcessingResult:
    metadata_path = artifact_dir / "metadata.json"
    observations_path = artifact_dir / "observations.json"
    summary_path = artifact_dir / "tracking_summary.json"
    try:
        batch = ObservationTransformer().load(
            metadata_path,
            observations_path,
            _PLACEHOLDER_VIDEO_ID,
            summary_path if summary_path.is_file() else None,
        )
        metadata = read_json(metadata_path)
        labels = {o.object_id: o.label for o in batch.objects}
        tracking_ids = {o.object_id: o.tracking_id for o in batch.objects}
        return VideoProcessingResult(
            duration_seconds=metadata.get("duration_seconds"),
            frame_count=metadata.get("frame_count"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            objects=[
                TrackedObjectResult(
                    tracking_id=o.tracking_id,
                    label=o.label,
                    first_seen_seconds=o.first_seen_ms / 1000,
                    last_seen_seconds=o.last_seen_ms / 1000,
                )
                for o in batch.objects
            ],
            observations=[
                ObservationResult(
                    tracking_id=tracking_ids[o.object_id],
                    timestamp_seconds=o.timestamp_ms / 1000,
                    frame_number=o.frame_index,
                    label=labels[o.object_id],
                    confidence=o.confidence,
                    bbox=o.bounding_box,
                    evidence_uri=o.evidence_uri,
                )
                for o in batch.observations
            ],
        )
    except ValueError as exc:
        raise SamProcessingError(f"Invalid SAM output in {artifact_dir}: {exc}") from exc
