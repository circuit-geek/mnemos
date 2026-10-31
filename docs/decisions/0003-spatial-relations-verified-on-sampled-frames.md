# 0003: Spatial relations are verified by Muse Spark on sampled frames

Status: accepted (2026-10-31)

## Context

Bounding boxes alone cannot establish `ON`, `NEXT_TO`, `NEAR` or `INSIDE`; overlapping boxes do
not imply a physical relation. Running a vision model on every frame is too slow and costly.

## Decision

- Every `SCENE_SAMPLE_INTERVAL_MS` (default 2 s), for samples where at least two tracked objects
  are visible, Muse Spark receives the frame image plus the visible objects (id, label, normalised
  box) and returns relations, which are validated (known IDs, allowed types, confidence threshold).
- Detections become validity intervals (`valid_from_ms <= t < valid_to_ms`). A relation closes only
  at a verified sample where both objects are visible and it is no longer reported. A visibility
  gap or a failed model call never closes it.
- Stored as typed Neo4j edges between `Object` nodes, replaced per video on re-analysis. Retrieval
  uses fixed Cypher and in-memory filtering; the model never writes queries.
- If scene analysis fails the video still completes with its temporal memory.

## Consequences

- Interval boundaries are accurate only to the sampling interval, and `NEAR`/`NEXT_TO` can flip
  between samples. Both are stated in answers.
- A relation not listed means "not verified", not "false"; the answering prompt says so.
- Cost grows with video length (about one Muse call per sample).
