import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "test_sam_video.py"
spec = importlib.util.spec_from_file_location("sam_video_experiment", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SamVideoParsingTests(unittest.TestCase):
    def test_annotation_times_do_not_bleed_into_next_frame(self):
        self.assertEqual(module.ass_time(10.301889), "0:00:10.30")
        self.assertEqual(module.ass_time(10.335222), "0:00:10.33")

    def test_tracks_gaps_and_inclusive_boxes(self):
        raw = (
            "<0f>7<|box;x1=10;y1=20;x2=14;y2=24;w=100;h=80|><|mask;x=0;y=0;data=5,5,!!!!!|>\n"
            "<2f>7<|box;x1=20;y1=20;x2=24;y2=24;w=100;h=80|><|mask;x=0;y=0;data=5,5,!!!!!|>\n"
            "<3f>8<|box;x1=30;y1=20;x2=34;y2=24;w=100;h=80|><|mask;x=0;y=0;data=5,5,!!!!!|>\n"
        )
        records = module.parse_sam_text(raw, 100, 80, 4)
        observations = module.normalize(records, "duster", [0, .1, .2, .3])
        tracks = module.summarize(observations, 4)
        self.assertEqual(observations[0]["bbox_xyxy"], [10, 20, 15, 25])
        self.assertEqual(tracks["7"]["missing_frames_between_detections"], [1])
        self.assertTrue(tracks["7"]["reappeared_after_gap"])
        self.assertEqual(tracks["8"]["first_observed_frame"], 3)

    def test_rejects_wrong_media_dimensions(self):
        raw = "<0f>0<|box;x1=1;y1=1;x2=2;y2=2;w=99;h=80|><|mask;x=0;y=0;data=1,1,!|>\n"
        with self.assertRaises(ValueError):
            module.parse_sam_text(raw, 100, 80, 1)


if __name__ == "__main__":
    unittest.main()
