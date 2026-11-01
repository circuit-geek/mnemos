#!/usr/bin/env python3
"""Record a processed video's memory and real Muse Spark answers as test fixtures.

Usage (backend running, videos processed):
  uv run python scripts/record_scenario_fixtures.py scenario_2=<video_id> --out fixtures/scenarios

Writes `<name>.json` with the memory bundle (observations as compact rows
[object_index, timestamp_ms, frame_index, left, top, right, bottom]) and, per question, the
interpreted intent and the evidence the answer cited. Tests replay these, so no model calls are
needed in unit tests. `--reuse-cases` refreshes only the memory and keeps recorded answers.
"""

import argparse
import json
from pathlib import Path
from urllib import request

QUESTIONS = {
    "scenario_1": [
        "Where was the mug last seen?",
        "When did the mug disappear from view?",
        "What happened to the mug?",
        "What is near the laptop at 18 seconds?",
        "What was next to the laptop at the start?",
        "How is the scene different at the end compared to the start?",
    ],
    "scenario_2": [
        "What changed in this video?",
        "How is the scene different at the end compared to the start?",
        "Compare 5 seconds and 15 seconds",
        "What is next to the notebook?",
        "What was near the pen at 17 seconds?",
        "Is the mug on the notebook?",
        "Which objects were on the desk before the notebook appeared?",
        "When did the phone appear?",
        "What happened between 5 and 10 seconds?",
        "Where was the mug last seen?",
        "What is the weather like?",
    ],
    "scenario_3": [
        "What is the mug on?",
        "What is next to the pen?",
        "What changed between 15 and 22 seconds?",
        "When did the mug appear?",
    ],
}
API = "http://localhost:8000/api/v1/videos"


def call(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=180) as res:
        return json.loads(res.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="+", help="name=video_id")
    parser.add_argument("--out", type=Path, default=Path("fixtures/scenarios"))
    parser.add_argument("--reuse-cases", action="store_true",
                        help="keep the recorded questions and answers; do not call the model")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for pair in args.videos:
        name, video_id = pair.split("=")
        bundle = call(f"{API}/{video_id}/memory")
        index = {o["object_id"]: i for i, o in enumerate(bundle["objects"])}
        rows = [[index[o["object_id"]], o["timestamp_ms"], o["frame_index"], *o["bounding_box"]]
                for o in bundle["observations"]]
        path = args.out / f"{name}.json"
        cases = []
        if args.reuse_cases and path.is_file():
            cases = json.loads(path.read_text())["cases"]
        for question in [] if cases else QUESTIONS.get(name, []):
            answer = call(f"{API}/{video_id}/ask", {"question": question})
            cases.append({
                "question": question,
                "intent": answer["intent"],
                "answer": answer["answer"],
                "sufficient_evidence": answer["sufficient_evidence"],
                "cited": [e["text"] for e in answer["evidence"]],
            })
            print(f"{name}: {question!r} -> {answer['intent']['intent']}")
        fixture = {
            "name": name,
            "objects": bundle["objects"],
            "events": [{k: e[k] for k in ("event_id", "object_id", "event_type", "start_time_ms",
                                          "end_time_ms", "description")}
                       for e in bundle["events"] if not e["event_id"].count(":")],
            "relationships": [{k: r[k] for k in ("relationship_id", "subject_object_id",
                                                 "target_object_id", "relation_type", "valid_from_ms",
                                                 "valid_to_ms", "last_verified_ms",
                                                 "evidence_timestamp_ms", "confidence", "reason")}
                              for r in bundle["relationships"]],
            "observations": rows,
            "cases": cases,
        }
        path.write_text(json.dumps(fixture, separators=(",", ":")))
        print(f"wrote {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
