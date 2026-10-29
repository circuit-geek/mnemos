import json
import shutil
from pathlib import Path

import pytest

from backend.core.exceptions import SamProcessingError
from backend.integrations.meta.sam_parser import parse_sam_artifacts

from .conftest import FIXTURE_DIR


def test_fixture_is_normalized():
    result = parse_sam_artifacts(FIXTURE_DIR)

    assert result.frame_count == 4
    assert {o.tracking_id for o in result.objects} == {"1", "2"}
    track_2 = next(o for o in result.objects if o.tracking_id == "2")
    assert track_2.first_seen_seconds == pytest.approx(0.033)
    assert track_2.last_seen_seconds == pytest.approx(0.1)
    assert len(result.observations) == 5
    first = result.observations[0]
    assert (first.tracking_id, first.frame_number, first.bbox) == ("1", 0, [100, 100, 200, 200])
    assert first.label == "mug"


def test_malformed_output_raises(tmp_path: Path):
    shutil.copytree(FIXTURE_DIR, tmp_path / "bad")
    observations = tmp_path / "bad" / "observations.json"
    rows = json.loads(observations.read_text())
    rows[0]["bbox_xyxy"] = [1, 2, 3]
    observations.write_text(json.dumps(rows))

    with pytest.raises(SamProcessingError):
        parse_sam_artifacts(tmp_path / "bad")
