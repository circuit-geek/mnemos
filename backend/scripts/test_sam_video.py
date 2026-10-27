#!/usr/bin/env python3
"""Standalone SAM 3.1 video experiment. Reads MODEL_API_KEY only from the process environment."""

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("META_API_KEY")


FRAME = re.compile(r"<([0-9]+)f(?:;[^>]*)?>")
RECORD = re.compile(r",?([0-9]+)(<\|box;[^|]*\|>)(<\|mask;[^|]*\|>)")
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "outputs" / "sam_experiments"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def probe_video(path):
    if not path.is_file():
        raise ValueError(f"Video does not exist: {path}")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise ValueError("No readable video stream")
    stream = data["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    fps = float(Fraction(stream.get("avg_frame_rate") or stream["r_frame_rate"]))
    duration = float(stream.get("duration") or data["format"]["duration"])
    frame_count = int(stream.get("nb_frames") or round(duration * fps))
    if width <= 0 or height <= 0 or fps <= 0 or frame_count <= 0:
        raise ValueError("Invalid video metadata")
    # Decoding one frame catches broken files that have a valid container header.
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    if decoded.returncode:
        raise ValueError(f"Video cannot be decoded: {decoded.stderr.strip()}")
    frames = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "frame=best_effort_timestamp_time", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    timestamps = [float(f["best_effort_timestamp_time"]) for f in json.loads(frames.stdout)["frames"]]
    if len(timestamps) != frame_count:
        raise ValueError("Decoded frame count disagrees with video metadata")
    return {"source_video": str(path.resolve()), "width": width, "height": height,
            "fps": fps, "duration_seconds": duration, "frame_count": frame_count,
            "frame_timestamps_seconds": timestamps}


def token_fields(token):
    return dict(part.split("=", 1) for part in token[2:-2].split(";")[1:] if "=" in part)


def parse_sam_text(raw, width, height, frame_count):
    """Parse documented concept output; fail closed on unexpected geometry/grammar."""
    if not raw.strip():
        return []
    records = []
    markers = list(FRAME.finditer(raw))
    if not markers or raw[:markers[0].start()].strip():
        raise ValueError("SAM output has no valid frame marker")
    seen = set()
    for i, marker in enumerate(markers):
        frame = int(marker.group(1))
        if frame >= frame_count:
            raise ValueError(f"SAM frame {frame} exceeds source frame count")
        body = raw[marker.end():markers[i + 1].start() if i + 1 < len(markers) else len(raw)].strip()
        cursor = 0
        for match in RECORD.finditer(body):
            if body[cursor:match.start()].strip():
                raise ValueError(f"Unparsed SAM content at frame {frame}")
            track_id, box_token, mask_token = match.groups()
            box = token_fields(box_token)
            mask = token_fields(mask_token)
            try:
                x1, y1, x2, y2 = (int(box[k]) for k in ("x1", "y1", "x2", "y2"))
                token_width, token_height = int(box["w"]), int(box["h"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Invalid box at frame {frame}") from exc
            if (token_width, token_height) != (width, height):
                raise ValueError(f"SAM box dimensions differ from source at frame {frame}")
            if not (0 <= x1 <= x2 < width and 0 <= y1 <= y2 < height):
                raise ValueError(f"SAM box outside source dimensions at frame {frame}")
            if mask.get("x") != "0" or mask.get("y") != "0" or "data" not in mask:
                raise ValueError(f"Invalid mask token at frame {frame}")
            if (frame, track_id) in seen:
                raise ValueError(f"Duplicate track {track_id} on frame {frame}")
            seen.add((frame, track_id))
            records.append({"frame_index": frame, "tracking_id": track_id,
                            "bbox_xyxy": [x1, y1, x2 + 1, y2 + 1],
                            "box_source": box, "mask_source": mask})
            cursor = match.end()
        if body[cursor:].strip():
            raise ValueError(f"Unparsed SAM content at frame {frame}")
    return records


def normalize(records, concept, timestamps):
    return [{"frame_index": item["frame_index"],
             "timestamp_seconds": timestamps[item["frame_index"]],
             "tracking_id": item["tracking_id"], "label": concept,
             "bbox_xyxy": item["bbox_xyxy"],
             "bbox_convention": "pixel half-open [left, top, right, bottom]",
             "evidence": "SAM 3.1 response in raw_response.txt"}
            for item in sorted(records, key=lambda r: (r["frame_index"], r["tracking_id"]))]


def summarize(observations, frame_count):
    grouped = defaultdict(list)
    for obs in observations:
        grouped[obs["tracking_id"]].append(obs)
    result = {}
    for track_id, entries in grouped.items():
        frames = sorted({entry["frame_index"] for entry in entries})
        missing = sorted(set(range(frames[0], frames[-1] + 1)) - set(frames))
        movement = []
        for entry in entries:
            left, top, right, bottom = entry["bbox_xyxy"]
            movement.append({"frame_index": entry["frame_index"],
                             "timestamp_seconds": entry["timestamp_seconds"],
                             "bbox_xyxy": entry["bbox_xyxy"],
                             "center_xy": [(left + right) / 2, (top + bottom) / 2]})
        result[track_id] = {"label": entries[0]["label"],
                            "first_observed_frame": frames[0], "last_observed_frame": frames[-1],
                            "total_frames_detected": len(frames),
                            "missing_frames_between_detections": missing,
                            "not_detected_before_first": list(range(frames[0])),
                            "not_detected_after_last": list(range(frames[-1] + 1, frame_count)),
                            "reappeared_after_gap": bool(missing),
                            "bbox_movement": movement}
    return result


def upload_and_segment(path, concept, output, api_key):
    from openai import OpenAI

    client = OpenAI(base_url="https://api.meta.ai/v1", api_key=api_key)
    with path.open("rb") as video:
        uploaded = client.files.create(file=video, purpose="user_data")
    write_json(output / "upload_response.json", uploaded.model_dump(mode="json"))
    completed = False
    with (output / "raw_events.jsonl").open("w", encoding="utf-8") as event_file, \
            (output / "raw_response.txt").open("w", encoding="utf-8") as raw_file:
        with client.responses.stream(model="sam-3.1", input=[{
            "type": "message", "role": "user", "content": [
                {"type": "input_text", "text": concept},
                {"type": "input_video", "file_id": uploaded.id},
            ]}]) as stream:
            for event in stream:
                # Some SDK events include the cumulative response. Persist the
                # deltas and terminal event; raw_response.txt holds their text.
                if event.type in ("response.output_text.delta", "response.completed", "response.failed", "error"):
                    event_file.write(event.model_dump_json() + "\n")
                    event_file.flush()
                if event.type == "response.output_text.delta":
                    raw_file.write(event.delta)
                    raw_file.flush()
                elif event.type == "response.completed":
                    completed = True
                elif event.type in ("response.failed", "error"):
                    raise RuntimeError(f"SAM stream ended with {event.type}")
    if not completed:
        raise RuntimeError("SAM stream ended without response.completed")
    return (output / "raw_response.txt").read_text(encoding="utf-8")


def ass_time(seconds):
    # Start/end at the centisecond before the frame timestamp so a cue cannot
    # persist into the following source frame (ASS has 10 ms precision).
    centiseconds = math.floor(seconds * 100 + 1e-8)
    hours, rem = divmod(centiseconds, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{cs:02}"


def render_annotations(video, output, metadata, observations):
    """Draw only verified boxes. ASS uses source pixel coordinates and original timestamps."""
    if not observations:
        return "No detections; annotated video omitted."
    grouped = defaultdict(list)
    for obs in observations:
        grouped[obs["frame_index"]].append(obs)
    ass = output / "annotations.ass"
    header = ("[Script Info]\nScriptType: v4.00+\n"
              f"PlayResX: {metadata['width']}\nPlayResY: {metadata['height']}\n"
              "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
              "Style: Default,DejaVu Sans,18,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,0,7,0,0,0,1\n"
              "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [header]
    timestamps = metadata["frame_timestamps_seconds"]
    duration = metadata["duration_seconds"]
    for frame, entries in sorted(grouped.items()):
        start = timestamps[frame]
        end = timestamps[frame + 1] if frame + 1 < len(timestamps) else duration
        if end <= start:
            end = start + 1 / metadata["fps"]
        for obs in entries:
            x1, y1, x2, y2 = obs["bbox_xyxy"]
            label = f"{obs['label']} ID {obs['tracking_id']}  {start:.3f}s"
            label = label.replace("{", "(").replace("}", ")").replace("\\", "/")
            # ASS vector path draws a real rectangle in source pixel coordinates.
            box = f"{{\\an7\\pos(0,0)\\p1\\1a&HFF&\\bord2\\3c&H00FF00&}}m {x1} {y1} l {x2} {y1} {x2} {y2} {x1} {y2} {x1} {y1}"
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{box}\n")
            lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{{\\an7\\pos({x1},{max(0, y1 - 24)})}}{label}\n")
    ass.write_text("".join(lines), encoding="utf-8")
    rendered = output / "annotated_video.mp4"
    command = ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"ass={ass}",
               "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", str(rendered)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        rendered.unlink(missing_ok=True)
        return f"Annotation render unavailable: {result.stderr.strip()}"
    return "Bounding-box annotation generated; masks were preserved but not decoded."


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Source video file")
    parser.add_argument("--concept", default="duster", help="One noun phrase (default: duster)")
    args = parser.parse_args(argv)
    concept = args.concept.strip()
    if not concept or "\n" in concept:
        parser.error("--concept must be one nonempty noun phrase")
    try:
        metadata = probe_video(args.video)
        key = os.environ.get("MODEL_API_KEY")
        if not key:
            raise RuntimeError("MODEL_API_KEY is absent from the process environment (Properties). No .env was read.")
        slug = re.sub(r"[^a-z0-9]+", "_", concept.lower()).strip("_")[:40] or "concept"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        output = OUTPUT_ROOT / f"{slug}_{stamp}"
        output.mkdir(parents=True, exist_ok=False)
        metadata.update({"concept": concept, "model": "sam-3.1", "created_at_utc": stamp})
        write_json(output / "metadata.json", metadata)
        raw = upload_and_segment(args.video, concept, output, key)
        parsed = parse_sam_text(raw, metadata["width"], metadata["height"], metadata["frame_count"])
        write_json(output / "parsed_response.json", parsed)
        observations = normalize(parsed, concept, metadata["frame_timestamps_seconds"])
        write_json(output / "observations.json", observations)
        tracks = summarize(observations, metadata["frame_count"])
        write_json(output / "tracking_summary.json", {
            "tracks": tracks,
            "interpretation": "Track IDs are request-scoped model identifiers, not verified physical identities. Detection gaps do not prove occlusion or departure; end gaps do not prove exit from view.",
        })
        note = render_annotations(args.video, output, metadata, observations)
        (output / "visualization_note.txt").write_text(note + "\n", encoding="utf-8")
        print(f"Output: {output}\nTracks: {len(tracks)}\n{note}")
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
