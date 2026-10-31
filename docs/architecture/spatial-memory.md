# Spatial memory

Relations between tracked objects (`ON`, `NEXT_TO`, `NEAR`, `INSIDE`), each valid over a time interval.

## Pipeline

```text
Muse Spark names the objects in the video (concept discovery)
  -> SAM (one run per concept, tracks merged) -> objects/observations/events (temporal memory)
  -> SceneAnalyzer: sample a frame every SCENE_SAMPLE_INTERVAL_MS (default 2 s) where >= 2 objects are visible
  -> Muse Spark gets the frame image + visible objects (alias, label, normalised box)
  -> validated relations -> build_relationships() -> Neo4j typed edges
```

- **Concept discovery.** The SAM script tracks one noun phrase per run, so something must say what to track.
  `ConceptDiscoverer` samples `SAM_DISCOVERY_FRAMES` (6) frames across the whole video, sends them to Muse
  Spark in one call, and gets back short object names. Names are normalised, deduplicated, capped at
  `SAM_MAX_CONCEPTS` (5) and filtered: surfaces (table, desk, floor) and body parts (hands) are not tracked
  objects. What to track is **per video**: the upload's optional `concepts` field (comma-separated, validated,
  max 8) is stored on the video as `requested_concepts` and wins; otherwise discovery runs for that video.
  If discovery fails or finds nothing, SAM falls back to the generic `SAM_CONCEPT` (default `object`) and
  logs a warning. The concepts actually run are saved as `tracked_concepts` and returned by `GET /videos/{id}`.
- **Multi-object tracking.** The client runs SAM once per concept, then prefixes tracking IDs (`mug-0`,
  `pen-0`) so runs cannot collide. A concept absent from the video returns no tracks and is not an error.
- **Verification, not geometry.** Boxes are hints; Muse decides from the image. Output is validated: unknown
  or identical object IDs, malformed entries and confidence below `SCENE_MIN_CONFIDENCE` are dropped.
  `CONTAINS` is stored once as the inverse `INSIDE`. `NEXT_TO` and `NEAR` are symmetric (one edge per pair).
- **Intervals.** A relation opens at its first detection and closes at the first verified sample where both
  objects are visible and it is no longer reported. A visibility gap or a failed model call never closes it.
  `valid_from_ms <= t < valid_to_ms`; `valid_to_ms = null` means it was still holding at `last_verified_ms`.
  Bounds are accurate only to the sampling interval.
- **Graph.** `(:Object)-[:ON|NEXT_TO|NEAR|INSIDE {relationship_id, video_id, valid_from_ms, valid_to_ms,
  last_verified_ms, evidence_timestamp_ms, confidence, reason}]->(:Object)`. Re-analysing a video replaces its
  relations in one transaction. Cypher is fixed templates per type; the model never writes queries.
- **Failure policy.** If scene analysis fails the video still completes with its temporal memory; the failure
  is logged (`Scene analysis failed; continuing without spatial memory`). Failed samples are skipped.

## Queries (`RELATIONSHIPS`, plus relations in `SCENE_AT_TIME`)

`object_label` anchors on either side of a relation; `relation_type` filters (asking for `NEAR` also returns
`NEXT_TO`); `time_seconds` or a window selects what held then; `before_appearance_of` resolves "before the
notebook appeared" to just before that object's first detection and lists the objects present. If the requested
type has no match, a note plus the relations that were verified are returned so the answer can say "not ON, but
NEXT_TO". Surfaces such as a desk are not tracked objects.

## Known limits

- Identity can split across an occlusion or a long absence (the same mug may become two tracks).
- `NEAR` and `NEXT_TO` can flip between samples, fragmenting intervals; they are distinct edges.
- One Muse call per sample: a 20 s clip is about 10 calls. Total processing is dominated by one SAM run per concept.
- Discovery is a model call, so it is not deterministic: it can add a concept that is not really there (that
  costs one empty SAM run) or miss a small object. Pass `concepts` on upload when it matters.
